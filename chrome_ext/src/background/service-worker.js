chrome.runtime.onMessage.addListener((message, sender, sendResponse) => {
  if (message.type !== "CHECK_CLAIM") {
    return;
  }

  fetch("http://127.0.0.1:8000/check", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ claim: message.claim }),
  })
    .then(async (response) => {
      if (!response.ok) {
        throw new Error(`Fact-check request failed (${response.status})`);
      }
      return response.json();
    })
    .then((result) => sendResponse(result))
    .catch(() => sendResponse({ error: "The fact-check service is unavailable." }));

  return true;
});

chrome.runtime.onInstalled.addListener(() => {
  console.log("TrustLens extension installed");
});
