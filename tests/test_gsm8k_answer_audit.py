import unittest

from analyses.gsm8k_answer_audit import extract, score


class AnswerTests(unittest.TestCase):
    def test_hash_line_is_not_entire_tail(self):
        r = extract("Work\n#### 210\nThe answer is: 210")
        self.assertEqual(r["value"], "210")
        self.assertEqual(len(r["claims"]), 2)

    def test_supported_presentations(self):
        for text, value in [(r"The answer is \boxed{\frac{1}{2}}.", "1/2"),
                            ("Answer: The two girls ate 13 apples altogether.", "13"),
                            ("So the answer is: 17", "17"),
                            ("Answer: $1,600.00.", "1600"),
                            ("Answer: -0.5 kg", "-1/2")]:
            with self.subTest(text=text):
                self.assertEqual(extract(text)["value"], value)

    def test_no_gold_fishing_or_arithmetic_evaluation(self):
        for text in ["We compute 13 apples.", "Answer: 12 or 13", "Answer: 1 2", "Answer: 3+4=7",
                     "Answer: 1e3", "Answer: 1,2", "Answer: approximately 13", r"\boxed{1 2}", r"\boxed{12"]:
            with self.subTest(text=text):
                self.assertNotEqual(extract(text)["status"], "parsed")

    def test_conflicts_do_not_choose_the_gold(self):
        text = "#### 4\nThe answer is: 5"
        for gold in ("4", "5"):
            r = score({"answer": gold}, text, True, False)
            self.assertFalse(r["answer_correct"])
            self.assertEqual(r["status"], "conflicting_marked_answers")

    def test_next_problem_is_separate_and_not_clean(self):
        text = "The answer is 4\n\nProblem: a new question\nThe answer is 150"
        r = score({"answer": "4"}, text, True, False)
        self.assertTrue(r["answer_correct"])
        self.assertTrue(r["correct_with_eos"])
        self.assertFalse(r["clean_correct"])

    def test_no_primary_credit_for_truncation_or_special_tokens(self):
        self.assertFalse(score({"answer": "4"}, "Answer: 4", False, True)["clean_correct"])
        self.assertFalse(score({"answer": "4"}, "Answer: 4<|im_end|>", True, False)["clean_correct"])


if __name__ == "__main__":
    unittest.main()
