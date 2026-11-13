# A6-2 9B paired M512 freeze

512 ordered training questions in both arms. All three required self-checks passed, including full MATH test and holdout exclusion. Selection processed 570 questions; qualifying rate 89.8246%. Every chosen long sequence fits2300tokens, has a verified correct final answer, and excludes thinking/end markers. Raw attempts, eligibility labels and original failure recovery are retained.

The two admitted arms each use512questions, two epochs, batch8,128updates,seed17. Predictions are frozen at18f64e2d before eligibility scoring and downstream scoring. These are exploratory, excluded from H0–H3. Construction plus both arms and reserved4B construction totals$16.7822 of the$50A6-2 cap. Generationv2 usage includes all18 savedv1 responses once.
