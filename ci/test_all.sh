for notebook in "AdvancedPif" "AdvancedQueries" "ImportVASP" "IntroQueries" "MLonCitrination" "WorkingWithPIFs"; do
  ~/anaconda3/bin/jupyter nbconvert --to notebook --execute --ExecutePreprocessor.timeout=300 --output tmp.ipynb ${notebook}.ipynb
  echo "Tested ${notebook} -^"
  rm -f tmp.ipynb
done

