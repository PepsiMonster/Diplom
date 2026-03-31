use crate::params::ScenarioConfig;

#[derive(Debug, Clone)]
pub struct Job {
    pub resource_demand: u32,
    pub remaining_workload: f64,
}

#[derive(Debug, Clone, Copy)]
pub enum RejectionReason {
    Capacity,
    Servers,
    Resource,
}

#[derive(Debug, Clone)]
pub struct SystemState {
    pub current_time: f64,
    pub active_jobs: Vec<Job>,
    pub occupied_resource_total: u32,
}

impl SystemState {
    pub fn new() -> Self {
        Self {
            current_time: 0.0,
            active_jobs: Vec::new(),
            occupied_resource_total: 0,
        }
    }

    pub fn num_jobs(&self) -> usize {
        self.active_jobs.len()
    }

    pub fn can_accept(&self, resource: u32, scenario: &ScenarioConfig) -> Result<(), RejectionReason> {
        if self.num_jobs() >= scenario.capacity_k {
            return Err(RejectionReason::Capacity);
        }
        if self.num_jobs() >= scenario.servers_n {
            return Err(RejectionReason::Servers);
        }
        if self.occupied_resource_total + resource > scenario.total_resource_r {
            return Err(RejectionReason::Resource);
        }
        Ok(())
    }

    pub fn add_job(&mut self, resource: u32, workload: f64) {
        self.active_jobs.push(Job {
            resource_demand: resource,
            remaining_workload: workload,
        });
        self.occupied_resource_total += resource;
    }

    pub fn advance_and_complete(&mut self, dt: f64, service_speed: f64) -> usize {
        self.current_time += dt;
        let mut completed = 0;
        for j in &mut self.active_jobs {
            j.remaining_workload = (j.remaining_workload - service_speed * dt).max(0.0);
        }
        let mut retained = Vec::with_capacity(self.active_jobs.len());
        for j in self.active_jobs.drain(..) {
            if j.remaining_workload <= 1e-12 {
                completed += 1;
                self.occupied_resource_total -= j.resource_demand;
            } else {
                retained.push(j);
            }
        }
        self.active_jobs = retained;
        completed
    }
}
