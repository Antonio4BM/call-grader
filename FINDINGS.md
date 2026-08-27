## Findings

The grader disagreed with the human labels on 12 of 75 criterion scores, for 84% exact agreement.

Most disagreements are the grader’s fault, especially in C2, where it systematically overcredits account verification or partial questioning as full needs discovery, and in C5, where it shows a leniency bias toward generally polite agents. C011 is different: the grader’s score may actually be defensible under the rubric, so I would review that human label before changing the model to match it.

C003 – C2 Discovery, human 5 vs grader 10. The grader treated a few questions and a summary of the customer’s goal as full discovery. The rubric requires understanding the customer’s situation before proposing anything and confirming that understanding. This looks like the grader is being too generous about what qualifies as complete discovery.

C005 – C2 Discovery, human 5 vs grader 10. The justification relies heavily on policy-number and renewal-notice questions. Those are closer to verification/account retrieval than full needs discovery.

C004 – C5 Professionalism, human 5 vs grader 10. The grader appears to overweight general courtesy and underweight lapses in call control, interruption, dismissiveness, or loss of thread.

C008 – C5 Professionalism, human 5 vs grader 10 The grader justificate the courteous but again underwight interruptions.

C011 – C4 Resolution, human 5 vs grader 10. The grader says the payment-method change was completed and that confirmation would arrive the same day. Under the rubric, a 10 is allowed when the customer’s reason for calling is resolved, even without a future owner/timeframe. If the customer’s request was in fact fully completed during the call, the grader’s 10 appears defensible. I would flag this as a possible human-label inconsistency or rubric interpretation issue rather than simply tuning the model toward the label.

## One more day

With one more day, I would focus on reliability rather than adding features. I would run repeated grading trials to measure variance, improve the prompt around the recurring C2 and C5 failure modes, and add a small review flag for ambiguous or high-risk disagreements. I would also inspect questionable human labels such as C011.