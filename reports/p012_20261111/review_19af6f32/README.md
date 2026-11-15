# Accepted A8 group B result review

Review 19af6f32186dbdc3f5286858abafa96b125256c3 accepts all seven B endpoints and the existing labels for all 9,233 outputs. The frozen A8 group criterion holds: 6/7 hits and mean residual +0.57pp. On the four K > 1 cells, RMSE is 2.44pp for the registered rule, 2.09pp for beta=1 and 6.56pp for beta=0. These numbers are transcribed from the accepted independent review.

B01 gsm8k/test/0744 is the only scoring disagreement. Its original incorrect label is preserved under the established format rule. Endpoint and packet AUDIT_STATUS.json sidecars carry acceptance; frozen RESULTS.json files, raw archives, labels and input manifest retain their hashes.

C is 1/5 complete and continues with the existing controller. T01/T03/T04 and reduced GSM8K remain active. T02 correctly waits for B/C completion under b24f787a R-1 before the exact source patch and single launch. All A8 checkpoints remain retained; report when Modal storage approaches 900 GiB. No additional experiment is authorized.
