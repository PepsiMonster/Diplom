# Переменные
MAIN = main
BUILD_DIR = build
# Используем wildcard, чтобы make точно «видел» список всех файлов
SOURCES = $(MAIN).tex $(wildcard sections/*.tex) bib/sources.bib
ARCHIVE_NAME = diplom_$(shell date +%Y%m%d_%H%M).zip

.PHONY: all clean archive

all: $(MAIN).pdf

# Главный PDF в корне теперь зависит от PDF в папке build
$(MAIN).pdf: $(BUILD_DIR)/$(MAIN).pdf
	cp $< $@

# Правило сборки самого PDF в папке build
$(BUILD_DIR)/$(MAIN).pdf: $(SOURCES)
	mkdir -p $(BUILD_DIR)
	# Первый запуск lualatex
	lualatex --output-directory=$(BUILD_DIR) --interaction=nonstopmode $(MAIN).tex
	# Сборка библиографии
	biber $(BUILD_DIR)/$(MAIN)
	# Повторные прогоны
	lualatex --output-directory=$(BUILD_DIR) --interaction=nonstopmode $(MAIN).tex
	lualatex --output-directory=$(BUILD_DIR) --interaction=nonstopmode $(MAIN).tex

clean:
	rm -rf $(BUILD_DIR)
	rm -f $(MAIN).pdf

archive: clean
	zip -r $(ARCHIVE_NAME) . -x "*.git*" "results/*"