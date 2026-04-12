
#define MAX_CAPACITY 128
#define RESOURCE_CHOICES 8
#define INF_TIME 1.0e300

__device__ __forceinline__ unsigned long long xorshift64star(unsigned long long* state) {
    unsigned long long x = *state;
    if (x == 0ULL) {
        x = 0x9E3779B97F4A7C15ULL;
    }
    x ^= x >> 12;
    x ^= x << 25;
    x ^= x >> 27;
    *state = x;
    return x * 2685821657736338717ULL;
}

__device__ __forceinline__ double uniform01(unsigned long long* state) {
    unsigned long long x = xorshift64star(state);
    double u = (double)((x >> 11) * (1.0 / 9007199254740992.0));
    if (u <= 1.0e-15) u = 1.0e-15;
    if (u >= 1.0) u = 1.0 - 1.0e-15;
    return u;
}

__device__ __forceinline__ double sample_exp(unsigned long long* state, double rate) {
    if (rate <= 0.0) return INF_TIME;
    double u = uniform01(state);
    return -log(u) / rate;
}

__device__ __forceinline__ double sample_erlang(unsigned long long* state, unsigned int order, double mean) {
    if (order == 0 || mean <= 0.0) return 0.0;
    double rate = ((double)order) / mean;
    double total = 0.0;
    for (unsigned int i = 0; i < order; ++i) {
        total += sample_exp(state, rate);
    }
    return total;
}

__device__ __forceinline__ double sample_hyperexp2(unsigned long long* state, double mean, double p, double fast_rate_multiplier) {
    if (mean <= 0.0 || fast_rate_multiplier <= 0.0 || p <= 0.0 || p >= 1.0) return 0.0;
    double rate_1 = fast_rate_multiplier / mean;
    double denominator = mean - p / rate_1;
    if (rate_1 <= 0.0 || denominator <= 0.0) return 0.0;
    double rate_2 = (1.0 - p) / denominator;
    if (rate_2 <= 0.0) return 0.0;
    if (uniform01(state) <= p) return sample_exp(state, rate_1);
    return sample_exp(state, rate_2);
}

__device__ __forceinline__ double sample_arrival_delta(
    unsigned long long* state,
    unsigned int mode,
    unsigned int order,
    double arrival_rate,
    double p,
    double fast_rate_multiplier
) {
    if (arrival_rate <= 0.0) return INF_TIME;

    if (mode == 0u) { // poisson
        return sample_exp(state, arrival_rate);
    }
    if (mode == 1u) { // erlang
        return sample_erlang(state, order, 1.0 / arrival_rate);
    }
    if (mode == 2u) { // hyperexp2
        return sample_hyperexp2(state, 1.0 / arrival_rate, p, fast_rate_multiplier);
    }
    return sample_exp(state, arrival_rate);
}

__device__ __forceinline__ double sample_workload_value(
    unsigned long long* state,
    unsigned int mode,
    unsigned int order,
    double mean,
    double p,
    double fast_rate_multiplier
) {
    if (mode == 0u) { // deterministic
        return mean;
    }
    if (mode == 1u) { // exponential
        return sample_exp(state, 1.0 / mean);
    }
    if (mode == 2u) { // erlang
        return sample_erlang(state, order, mean);
    }
    if (mode == 3u) { // hyperexp2
        return sample_hyperexp2(state, mean, p, fast_rate_multiplier);
    }
    return mean;
}

__device__ __forceinline__ double overlap_len(double a0, double a1, double b0, double b1) {
    double left = a0 > b0 ? a0 : b0;
    double right = a1 < b1 ? a1 : b1;
    double len = right - left;
    return len > 0.0 ? len : 0.0;
}

__device__ __forceinline__ unsigned int sample_resource(
    unsigned long long* state,
    unsigned int resource_len,
    unsigned int rv0, unsigned int rv1, unsigned int rv2, unsigned int rv3,
    unsigned int rv4, unsigned int rv5, unsigned int rv6, unsigned int rv7,
    double c0, double c1, double c2, double c3, double c4, double c5, double c6, double c7
) {
    double u = uniform01(state);

    unsigned int values[RESOURCE_CHOICES];
    double cdf[RESOURCE_CHOICES];

    values[0] = rv0; values[1] = rv1; values[2] = rv2; values[3] = rv3;
    values[4] = rv4; values[5] = rv5; values[6] = rv6; values[7] = rv7;

    cdf[0] = c0; cdf[1] = c1; cdf[2] = c2; cdf[3] = c3;
    cdf[4] = c4; cdf[5] = c5; cdf[6] = c6; cdf[7] = c7;

    for (unsigned int i = 0; i < resource_len; ++i) {
        if (u <= cdf[i]) {
            return values[i];
        }
    }

    return values[resource_len - 1];
}

extern "C" __global__ void simulate_loss_poisson_deterministic(
    unsigned int num_runs,
    double arrival_rate,
    double service_speed,
    double max_time,
    double warmup_time,
    unsigned int servers_n,
    unsigned int capacity_k,
    unsigned int total_resource_r,
    const unsigned long long* seeds,

    unsigned int arrival_mode,
    unsigned int arrival_order,
    double arrival_p,
    double arrival_fast_mult,

    unsigned int workload_mode,
    unsigned int workload_order,
    double workload_mean,
    double workload_p,
    double workload_fast_mult,

    unsigned int collect_state_times,

    unsigned int resource_len,
    unsigned int rv0, unsigned int rv1, unsigned int rv2, unsigned int rv3,
    unsigned int rv4, unsigned int rv5, unsigned int rv6, unsigned int rv7,
    double c0, double c1, double c2, double c3, double c4, double c5, double c6, double c7,

    unsigned long long* out_arrival_attempts,
    unsigned long long* out_accepted_arrivals,
    unsigned long long* out_rejected_arrivals,
    unsigned long long* out_rejected_capacity,
    unsigned long long* out_rejected_server,
    unsigned long long* out_rejected_resource,
    unsigned long long* out_completed_jobs,
    unsigned long long* out_completed_time_samples,

    double* out_resource_time,
    double* out_service_time_sum,
    double* out_service_time_sq_sum,
    double* out_sojourn_time_sum,
    double* out_sojourn_time_sq_sum,

    double* out_state_times
) {
    unsigned int run_id = blockIdx.x * blockDim.x + threadIdx.x;
    if (run_id >= num_runs) {
        return;
    }

    if (capacity_k > MAX_CAPACITY) {
        return;
    }

    unsigned int state_offset = run_id * (capacity_k + 1);

    if (collect_state_times != 0u) {
        for (unsigned int k = 0; k <= capacity_k; ++k) {
            out_state_times[state_offset + k] = 0.0;
        }
    }

    out_arrival_attempts[run_id] = 0ULL;
    out_accepted_arrivals[run_id] = 0ULL;
    out_rejected_arrivals[run_id] = 0ULL;
    out_rejected_capacity[run_id] = 0ULL;
    out_rejected_server[run_id] = 0ULL;
    out_rejected_resource[run_id] = 0ULL;
    out_completed_jobs[run_id] = 0ULL;
    out_completed_time_samples[run_id] = 0ULL;

    out_resource_time[run_id] = 0.0;
    out_service_time_sum[run_id] = 0.0;
    out_service_time_sq_sum[run_id] = 0.0;
    out_sojourn_time_sum[run_id] = 0.0;
    out_sojourn_time_sq_sum[run_id] = 0.0;

    unsigned long long rng_state = seeds[run_id] ^ 0xD1B54A32D192ED03ULL;

    double current_time = 0.0;
    double next_arrival_time = sample_arrival_delta(
        &rng_state,
        arrival_mode,
        arrival_order,
        arrival_rate,
        arrival_p,
        arrival_fast_mult
    );

    double departure_times[MAX_CAPACITY];
    double arrival_times[MAX_CAPACITY];
    unsigned int resource_demands[MAX_CAPACITY];

    unsigned int active_count = 0;
    unsigned int occupied_resource = 0;

    while (current_time < max_time) {
        double next_departure_time = INF_TIME;

        for (unsigned int i = 0; i < active_count; ++i) {
            if (departure_times[i] < next_departure_time) {
                next_departure_time = departure_times[i];
            }
        }

        double next_event_time = next_arrival_time;
        if (next_departure_time < next_event_time) {
            next_event_time = next_departure_time;
        }
        if (max_time < next_event_time) {
            next_event_time = max_time;
        }

        double overlap = overlap_len(current_time, next_event_time, warmup_time, max_time);
        if (overlap > 0.0) {
            if (collect_state_times != 0u) {
                out_state_times[state_offset + active_count] += overlap;
            }
            out_resource_time[run_id] += ((double)occupied_resource) * overlap;
        }

        current_time = next_event_time;
        if (current_time >= max_time - 1.0e-12) {
            break;
        }

        int arrival_happened = (next_arrival_time <= next_departure_time + 1.0e-12);

        if (arrival_happened) {
            if (current_time >= warmup_time && current_time <= max_time) {
                out_arrival_attempts[run_id] += 1ULL;
            }

            unsigned int demand = sample_resource(
                &rng_state,
                resource_len,
                rv0, rv1, rv2, rv3, rv4, rv5, rv6, rv7,
                c0, c1, c2, c3, c4, c5, c6, c7
            );

            int accepted = 0;

            if (active_count >= capacity_k) {
                if (current_time >= warmup_time && current_time <= max_time) {
                    out_rejected_arrivals[run_id] += 1ULL;
                    out_rejected_capacity[run_id] += 1ULL;
                }
            } else if (active_count >= servers_n) {
                if (current_time >= warmup_time && current_time <= max_time) {
                    out_rejected_arrivals[run_id] += 1ULL;
                    out_rejected_server[run_id] += 1ULL;
                }
            } else if (occupied_resource + demand > total_resource_r) {
                if (current_time >= warmup_time && current_time <= max_time) {
                    out_rejected_arrivals[run_id] += 1ULL;
                    out_rejected_resource[run_id] += 1ULL;
                }
            } else {
                accepted = 1;
            }

            if (accepted) {
                double workload = sample_workload_value(
                    &rng_state,
                    workload_mode,
                    workload_order,
                    workload_mean,
                    workload_p,
                    workload_fast_mult
                );
                double service_time = workload / service_speed;
                if (service_time < 0.0) {
                    service_time = 0.0;
                }
                departure_times[active_count] = current_time + service_time;
                arrival_times[active_count] = current_time;
                resource_demands[active_count] = demand;
                active_count += 1;
                occupied_resource += demand;

                if (current_time >= warmup_time && current_time <= max_time) {
                    out_accepted_arrivals[run_id] += 1ULL;
                }
            }

            double delta = sample_arrival_delta(
                &rng_state,
                arrival_mode,
                arrival_order,
                arrival_rate,
                arrival_p,
                arrival_fast_mult
            );
            next_arrival_time = (delta >= INF_TIME / 2.0) ? INF_TIME : (current_time + delta);
        } else {
            unsigned int i = 0;
            while (i < active_count) {
                if (departure_times[i] <= current_time + 1.0e-12) {
                    double service_time = departure_times[i] - arrival_times[i];
                    double sojourn_time = service_time;

                    if (current_time >= warmup_time && current_time <= max_time) {
                        out_completed_jobs[run_id] += 1ULL;
                        out_completed_time_samples[run_id] += 1ULL;

                        out_service_time_sum[run_id] += service_time;
                        out_service_time_sq_sum[run_id] += service_time * service_time;

                        out_sojourn_time_sum[run_id] += sojourn_time;
                        out_sojourn_time_sq_sum[run_id] += sojourn_time * sojourn_time;
                    }

                    occupied_resource -= resource_demands[i];

                    unsigned int last = active_count - 1;
                    departure_times[i] = departure_times[last];
                    arrival_times[i] = arrival_times[last];
                    resource_demands[i] = resource_demands[last];
                    active_count -= 1;
                } else {
                    i += 1;
                }
            }
        }
    }
}
