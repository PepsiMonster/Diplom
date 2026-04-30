# Обманка для фильтров pandoc-xnos, чтобы они корректно работали с Pandoc 3.8
export PANDOC_VERSION=2.16

# Указываем Python искать библиотеку pandocxnos в локальной папке проекта
# $(CURDIR) — это встроенная переменная make, указывающая на текущую директорию
export PYTHONPATH := $(PYTHONPATH):$(CURDIR)/pandoc/filters

FILES = $(patsubst %.md, %.docx, $(wildcard *.md))
FILES += $(patsubst %.md, %.pdf, $(wildcard *.md))

FILTERS =
OPTIONS =
PDF_ENGINE =
PDF_OPTIONS =
FORMAT_OPTIONS =

### Cross references
## Use pandoc-xnos (https://github.com/tomduck/pandoc-xnos)
## Local pandoc-xnos
FILTERS += --filter pandoc/filters/pandoc_fignos.py 
FILTERS += --filter pandoc/filters/pandoc_eqnos.py 
FILTERS += --filter pandoc/filters/pandoc_tablenos.py 
FILTERS += --filter pandoc/filters/pandoc_secnos.py

## System-wide pandoc-xnos (закомментировано, так как используем локальные)
# FILTERS += --filter pandoc-fignos --filter pandoc-eqnos --filter pandoc-tablenos --filter pandoc-secnos

## Use pandoc-crossref (https://github.com/lierdakil/pandoc-crossref)
# FILTERS += --filter pandoc-crossref
###

PDF_ENGINE += --pdf-engine=lualatex --pdf-engine-opt=--shell-escape
OPTIONS += --number-sections
BIB_OPTIONS = --citeproc

%.docx: %.md
	-pandoc "$<" $(FILTERS) $(OPTIONS) $(BIB_OPTIONS) -o "$@"

%.pdf: %.md
	-pandoc "$<" $(FILTERS) $(PDF_ENGINE) $(PDF_OPTIONS) $(BIB_OPTIONS) $(FORMAT_OPTIONS) $(OPTIONS) -o "$@"

all: $(FILES)

clean:
	-rm -f $(FILES) *~

cleanall: clean