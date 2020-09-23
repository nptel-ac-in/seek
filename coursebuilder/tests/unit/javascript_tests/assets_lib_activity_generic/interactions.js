/**
 * Copyright 2020 Google LLC
 *
 * Licensed under the Apache License, Version 2.0 (the "License");
 * you may not use this file except in compliance with the License.
 * You may obtain a copy of the License at
 *
 *      http://www.apache.org/licenses/LICENSE-2.0
 *
 * Unless required by applicable law or agreed to in writing, software
 * distributed under the License is distributed on an "AS IS" BASIS,
 * WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
 * See the License for the specific language governing permissions and
 * limitations under the License.
 */

{
  "multiple_choice_activity": [{
    "questionType": "multiple choice",
    "choices": [
      ["A", true, "Correct."],
      ["B", false, "Incorrect"],
      ["C", false, "Incorrect"],
      ["D", false, "Incorrect"]
    ]
  }],

  "multiple_choice_group_activity": [{
    "questionType": "multiple choice group",
    "questionsList": [
      {
        "choices": ["A", "B", "C"],
        "correctIndex": 0
      },
      {
        "choices": ["Yes", "No"],
        "correctIndex": 1
      }
    ]
  }],

  "free_text_activity": [{
    "questionType": "freetext",
    "correctAnswerRegex": /42/i,
    "correctAnswerOutput": "Correct!",
    "incorrectAnswerOutput": "Wrong!",
    "showAnswerOutput": "The correct answer is 42 (of course)."
  }],

  "mixed_assessment": {
    "preamble": "This is an assessment.",
    "checkAnswers": true,
    "questionsList": [
      {
        "questionHTML": "Multiple choice question.",
        "choices": [correct("A"), "B", "C", "D"],
        "lesson": "1.1"
      },
      {
        "questionHTML": "String question.",
        "correctAnswerString": "Rectus",
        "lesson": "1.1"
      },
      {
        "questionHTML": "Regex question.",
        "correctAnswerRegex": /match/i,
        "lesson": "1.1"
      },
      {
        "questionHTML": "Numeric question.",
        "correctAnswerNumeric": 42,
        "lesson": "1.1"
      }
    ]
  },
}
