#!/bin/bash

# Базовые пути
BASE_DIR=~/study/Diplom
DEST_DIR="$BASE_DIR/tex/images_appendix"

# Создаем папку для картинок приложения, если ее нет
mkdir -p "$DEST_DIR"

# Папки-источники с результатами экспериментов
SRC_WORKLOAD="$BASE_DIR/prog_GPU/results/20260430_150147__workload-sensetivity/plots"
SRC_ARRIVAL="$BASE_DIR/prog_GPU/results/20260430_144450__arrival-sensetivity/plots"
SRC_COMBINED="$BASE_DIR/prog_GPU/results/20260430_143122__combined-sensetivity/plots_reworked3"

# Список файлов, которые мы включили в tex-код приложения
FILES_TO_COPY=(
    # --- Графики чувствительности к workload ---
    "workload_sensitivity_boxplot_loss_probability_sigma-1p2_lambda-90.png"
    "workload_sensitivity_boxplot_mean_sojourn_time_sigma-1p2_lambda-90.png"
    "workload_sensitivity_stationary_distribution_sigma-1p2_lambda-90.png"
    "workload_sensitivity_stationary_tail_sigma-1p2_lambda-90.png"

    # --- Графики чувствительности к arrival ---
    "arrival_sensitivity_boxplot_loss_probability_sigma-1p2_lambda-90.png"
    "arrival_sensitivity_boxplot_mean_sojourn_time_sigma-1p2_lambda-90.png"
    "arrival_sensitivity_rejection_breakdown_sigma-1p2_lambda-90.png"
    "arrival_sensitivity_stationary_tail_sigma-1p2_lambda-90.png"

    # --- Комбинированные графики (из plots_reworked3) ---
    "01_heatmap_workload_arrival_mean_num_jobs_sigma-1p2.png"
    "06_joint_delta_vs_det_poisson_mean_num_jobs_sigma-1p2.png"
    "02_compare_arrivals_fixed_workload_loss_probability_sigma-1p2.png"
    "03_compare_workloads_fixed_arrival_loss_probability_sigma-1p2.png"
    "09_stationary_tail_by_workload_lambda-90_sigma-1p2.png"
    "09_stationary_tail_by_workload_lambda-104_sigma-1p2.png"
)

echo "Копирование графиков для приложения в $DEST_DIR..."
copied_count=0

for file in "${FILES_TO_COPY[@]}"; do
    # Ищем файл в трех директориях и копируем
    if [ -f "$SRC_WORKLOAD/$file" ]; then
        cp "$SRC_WORKLOAD/$file" "$DEST_DIR/"
        echo " [+] $file"
        ((copied_count++))
    elif [ -f "$SRC_ARRIVAL/$file" ]; then
        cp "$SRC_ARRIVAL/$file" "$DEST_DIR/"
        echo " [+] $file"
        ((copied_count++))
    elif [ -f "$SRC_COMBINED/$file" ]; then
        cp "$SRC_COMBINED/$file" "$DEST_DIR/"
        echo " [+] $file"
        ((copied_count++))
    else
        echo " [!] ОШИБКА: Файл $file не найден ни в одной из папок!"
    fi
done

echo "----------------------------------------"
echo "Готово! Скопировано файлов: $copied_count из ${#FILES_TO_COPY[@]}"