# EBAE Sample Source Note

## Source and release

The supplementary firm context comes from the Banco de España Business
Activity Survey (EBAE) sample distributed through BELab. The data and guide
belong to the same release: `EBAE20T422T2_01`, covering 2020 Q4 to 2022 Q2.

**Citation used in the project:** Banco de España (2022), *Banco de España
Business Activity Survey (EBAE) microdata: BELab user guide*. DOI:
`10.48719/BELab.EBAE20T422T2_01`.

**Files used:**

- `data/raw/ebae_sample/SampleFile.EBAE20T422T2_01.csv`
  - SHA-256: `8a5a2db21a727f2ba9fdeb2f15f2034a0627233afc83de1ec92d4ef6cfc70bf5`
- `data/raw/ebae_sample/User_guide_BELab.EBAE20T422T2_01_en.pdf`
  - SHA-256: `824ed8818c9b3716bf7dd7d9b483905da5d99c904694c1375b666b84d7200d26`

The guide was downloaded from the official Banco de España website on
11 September 2026. The sample was downloaded by the student on 6 September
2026 and copied into this project on 7 September 2026.

## Verified content

- The file contains 47 quarterly observations from 15 distinct anonymised
  firm identifiers. It does not contain 47 independent firms.
- It covers waves 1 to 7, from 2020 Q4 to 2022 Q2.
- Across waves, some identifiers appear under more than one sector. The notebook therefore labels sector counts as non-exclusive firm-sector pairs, rather than implying that they add up to 15 separate firms.
- The `impguerra_sum` variable is available in wave 7. Eight firms have a
  recorded answer: two `Very negative`, three `Negative`, three `Neutral`
  and none `Positive`.
- The matching guide defines four valid response categories for this variable:
  1 `Very negative`, 2 `Negative`, 3 `Neutral`, and 4 `Positive`.
- The EBAE firm identifier and the BOE awardee display ID are different and
  are never joined.

## Role in the project

The sample is supplementary secondary data. It demonstrates careful ingestion
of an anonymised firm-survey file and gives descriptive business context for
the war-in-Ukraine event family. It is not used to calculate the PGER score,
to estimate performance, or to make a claim about a BOE awardee.
