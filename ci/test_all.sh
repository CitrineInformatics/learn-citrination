for notebook in "AdvancedPif" "AdvancedQueries" "ImportInstron" "ImportVASP" "IntroQueries" "Journal Paper to Model Demo" "MLonCitrination" "t-SNE API" "WorkingWithPIFs"; do
  ~/anaconda3/bin/jupyter nbconvert --to notebook --execute --ExecutePreprocessor.timeout=300 --output tmp.ipynb ${notebook}.ipynb
  echo "Tested ${notebook} -^"
  rm -f tmp.ipynb
done

