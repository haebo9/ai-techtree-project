import assert from "node:assert/strict";

import { isInterviewClosingTranscript } from "../lib/interviewClosing.js";

const closingPhrases = [
  "오늘 면접은 여기까지 진행하겠습니다.",
  "이상으로 면접을 마치겠습니다.",
  "오늘 인터뷰는 여기까지 하겠습니다.",
  "면접을 마무리하겠습니다.",
];

const nonClosingPhrases = [
  "좋은 결과가 있기를 바라겠습니다.",
  "오늘 수고 많으셨습니다.",
  "고생 많으셨습니다. 다음 질문으로 넘어가겠습니다.",
  "여기까지 설명해 주신 내용은 잘 이해했습니다. 다음으로 협업 경험을 여쭤볼게요.",
];

for (const phrase of closingPhrases) {
  assert.equal(isInterviewClosingTranscript(phrase), true, phrase);
}

for (const phrase of nonClosingPhrases) {
  assert.equal(isInterviewClosingTranscript(phrase), false, phrase);
}

console.log("interview closing detection tests passed");
