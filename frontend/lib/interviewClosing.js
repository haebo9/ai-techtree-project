const INTERVIEW_CLOSING_PATTERNS = [
  /오늘\s*(면접|인터뷰)(은|는)?\s*여기까지\s*(진행하겠습니다|하겠습니다|하도록\s*하겠습니다)/,
  /이상으로\s*(오늘\s*)?(면접|인터뷰)(을|를)?\s*(마치겠습니다|마무리하겠습니다|종료하겠습니다)/,
  /(면접|인터뷰)(은|는)?\s*여기까지\s*(진행하겠습니다|하겠습니다|하도록\s*하겠습니다)/,
  /(면접|인터뷰)(을|를)?\s*(마치겠습니다|마무리하겠습니다|종료하겠습니다)/,
];

export function isInterviewClosingTranscript(text) {
  const normalized = String(text || "").replace(/\s+/g, " ").trim();
  if (!normalized) return false;

  return INTERVIEW_CLOSING_PATTERNS.some((pattern) => pattern.test(normalized));
}
