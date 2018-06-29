#!/usr/bin/env bash
for i in {0..19..1}; do 
	scripts/go_plot.py --go_file="/dfs/scratch2/caruiz/code/goatools/experiments/test_files/test_approved_drug_disease_pair_${i}.txt" -r -o "experiments/${i}_reg.pdf"
done
