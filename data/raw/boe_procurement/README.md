# BOE source file

The raw BOE public-procurement CSV is intentionally not stored in this repository.
Download the exact frozen release and verify both published and project checksums:

```powershell
python src/download_boe_dataset.py
```

The script retrieves Version 3 from [Zenodo record 18712463](https://zenodo.org/records/18712463) and saves it here as `licitaciones_contrataciones_BOE_2014_2024.csv`.
