---
dataset_info:
  features:
  - name: source
    dtype: string
  - name: problem
    dtype: string
  - name: solution
    dtype: string
  - name: messages
    list:
    - name: content
      dtype: string
    - name: role
      dtype: string
  splits:
  - name: train
    num_bytes: 2495457595.0398345
    num_examples: 859494
  - name: test
    num_bytes: 290340.31593470514
    num_examples: 100
  download_size: 1234351634
  dataset_size: 2495747935.355769
configs:
- config_name: default
  data_files:
  - split: train
    path: data/train-*
  - split: test
    path: data/test-*
license: apache-2.0
task_categories:
- text-generation
language:
- en
tags:
- aimo
- math
pretty_name: NuminaMath CoT
---

# Dataset Card for NuminaMath CoT

## Dataset Description

- **Homepage:** https://projectnumina.ai
- **Repository:** https://github.com/project-numina/aimo-progress-prize
- **Paper:** https://github.com/project-numina/aimo-progress-prize/blob/main/report/numina_dataset.pdf
- **Leaderboard:**
- **Point of Contact:** [Jia Li](jia@projectnumina.ai)


### Dataset Summary

Approximately 860k math problems, where each solution is formatted in a Chain of Thought (CoT) manner. The sources of the dataset range from Chinese high school math exercises to US and international mathematics olympiad competition problems. The data were primarily collected from online exam paper PDFs and mathematics discussion forums. The processing steps include (a) OCR from the original PDFs, (b) segmentation into problem-solution pairs, (c) Translation into English, (d) realignment to produce a CoT reasoning format, and (e) final answer formatting.


### Source breakdown

| Source | Number of Samples |
| --- | --- |
| aops_forum | 30201 |
| amc_aime | 4072 |
| cn_k12 | 276591 |
| gsm8k | 7345 |
| math | 7478 |
| olympiads | 150581 |
| orca_math | 153334 |
| synthetic_amc | 62111 |
| synthetic_math | 167895 |
| **Total** | **859608** |

### Licensing Information

The dataset is available under the [Apache License, Version 2.0](https://www.apache.org/licenses/LICENSE-2.0).

### Citation Information

```
@misc{numina_math_datasets,
  author = {Jia LI and Edward Beeching and Lewis Tunstall and Ben Lipkin and Roman Soletskyi and Shengyi Costa Huang and Kashif Rasul and Longhui Yu and Albert Jiang and Ziju Shen and Zihan Qin and Bin Dong and Li Zhou and Yann Fleureau and Guillaume Lample and Stanislas Polu},
  title = {NuminaMath},
  year = {2024},
  publisher = {Numina},
  journal = {Hugging Face repository},
  howpublished = {\url{[https://huggingface.co/AI-MO/NuminaMath-CoT](https://github.com/project-numina/aimo-progress-prize/blob/main/report/numina_dataset.pdf)}}
}
```
