(() => {
  const postSelector = "article";
  const badgeSelector = ".trustlens-post-badge";
  const badgeByPost = new Map();
  const postCleanupHandlers = new Map();
  const overlayLayer = document.createElement("div");
  overlayLayer.id = "trustlens-overlay-layer";
  overlayLayer.style.position = "fixed";
  overlayLayer.style.inset = "0";
  overlayLayer.style.zIndex = "2147483647";
  overlayLayer.style.pointerEvents = "none";
  document.body.append(overlayLayer);

  function getPostText(post) {
    return post.querySelector('[data-testid="tweetText"]')?.textContent.trim() || "";
  }

  function scanPostReputability(postText) {
    const suspiciousTerms = [
      "cures every",
      "guaranteed",
      "scientists confirm",
      "secret they do not want",
      "share this now",
    ];
    const normalizedText = postText.toLowerCase();
    const suspiciousTermCount = suspiciousTerms.filter((term) =>
      normalizedText.includes(term),
    ).length;

    if (suspiciousTermCount >= 2) {
      return { confidence: 20, label: "Low preliminary reputation" };
    }
    if (suspiciousTermCount === 1) {
      return { confidence: 45, label: "Moderate preliminary reputation" };
    }
    return { confidence: 78, label: "High preliminary reputation" };
  }

  function addBadge(post) {
    if (badgeByPost.has(post)) {
      return;
    }

    const postText = getPostText(post);
    if (!postText) {
      return;
    }

    const demoResultIndex = document.querySelectorAll(badgeSelector).length;
    const demoScan = [
      { confidence: 20, label: "Low preliminary reputation" },
      { confidence: 45, label: "Moderate preliminary reputation" },
      { confidence: 78, label: "High preliminary reputation" },
      { confidence: 28, label: "Low preliminary reputation" },
    ][demoResultIndex % 4];
    const scan = globalThis.chrome?.runtime?.sendMessage
      ? scanPostReputability(postText)
      : demoScan;

    post.classList.add("trustlens-post");

    const badge = document.createElement("button");
    badge.type = "button";
    badge.className = `trustlens-post-badge trustlens-confidence-${confidenceClass(scan.confidence)}`;
    badge.textContent = "?";
    badge.title = `${scan.label}. Click to fact check`;
    badge.setAttribute("aria-label", `Show TrustLens verdict for: ${postText}`);

    const panel = document.createElement("div");
    panel.className = "trustlens-panel";
    panel.hidden = true;
    const verdictElement = document.createElement("span");
    verdictElement.className = "trustlens-verdict";
    verdictElement.textContent = "Awaiting fact check";
    const confidenceElement = document.createElement("span");
    confidenceElement.className = "trustlens-confidence";
    confidenceElement.textContent = "Confidence: awaiting result";
    const divider = document.createElement("span");
    divider.className = "trustlens-divider";
    divider.textContent = "━━━━━━━━━━━━━━";
    const warningHeading = document.createElement("strong");
    warningHeading.className = "trustlens-warning-heading";
    warningHeading.textContent = "Please read this carefully:";
    const explanationElement = document.createElement("span");
    explanationElement.className = "trustlens-panel-explanation";
    explanationElement.textContent = "Click the badge to fact check this post.";
    const sourcesHeading = document.createElement("strong");
    sourcesHeading.className = "trustlens-sources-heading";
    sourcesHeading.textContent = "Sources";
    const sourcesElement = document.createElement("div");
    sourcesElement.className = "trustlens-sources";
    panel.append(
      verdictElement,
      confidenceElement,
      divider,
      warningHeading,
      explanationElement,
      sourcesHeading,
      sourcesElement,
    );
    let panelPinned = false;
    let verdictRequested = false;
    const listenerController = new AbortController();

    function requestVerdict() {
      if (verdictRequested) {
        return;
      }
      verdictRequested = true;
      verdictElement.textContent = "CHECKING...";

      if (!globalThis.chrome?.runtime?.sendMessage) {
        renderResult(demoResults[demoResultIndex % demoResults.length]);
        return;
      }

      chrome.runtime.sendMessage({ type: "CHECK_CLAIM", claim: postText }, (response) => {
        if (chrome.runtime.lastError || !response || response.error) {
          verdictElement.textContent = "Verdict: unavailable";
          explanationElement.textContent = response?.error || "The fact-check service is unavailable.";
          return;
        }

        renderResult(response);
      });
    }

    const demoResults = [
      {
        verdict: "False",
        confidence: 99,
        explanation:
          "The supplied evidence from WHO, Reuters, PolitiFact, FactCheck.org, and the CDC reports that large studies and reviews found no causal link between vaccines and autism. Claims that vaccines cause autism have been repeatedly evaluated and are characterized in the evidence as unsupported or false.",
        sources: [
          { title: "Kennedy says he told CDC to change website's language on autism and vaccines", url: "https://www.reuters.com/" },
          { title: "WHO expert group's new analysis reaffirms there is no link between vaccines and autism", url: "https://www.who.int/" },
          { title: "Viral image perpetuates misconception that vaccines cause autism - PolitiFact", url: "https://www.politifact.com/" },
          { title: "Revised CDC Website About Autism and Vaccines Is Not Evidence-Based - FactCheck.org", url: "https://www.factcheck.org/" },
          { title: "US CDC to award research contract on vaccines and autism", url: "https://www.cdc.gov/" },
        ],
      },
      {
        verdict: "Misleading",
        confidence: 82,
        explanation:
          "The post describes a real event but leaves out important context about the timing and scope of the announcement. Reputable reporting supports only part of the claim, so the wording gives a stronger impression than the evidence supports.",
        sources: [
          { title: "How to read health claims in the news", url: "https://www.who.int/news-room" },
          { title: "Reuters fact-checking and verification", url: "https://www.reuters.com/fact-check/" },
          { title: "Understanding misleading claims", url: "https://www.factcheck.org/" },
        ],
      },
      {
        verdict: "True",
        confidence: 91,
        explanation:
          "The claim is consistent with information published by the relevant public authority and is corroborated by independent reporting. The available evidence supports the main statement, although normal updates may change the details over time.",
        sources: [
          { title: "Official public information and updates", url: "https://www.gov.sg/" },
          { title: "Associated Press coverage", url: "https://apnews.com/" },
        ],
      },
      {
        verdict: "Unverified",
        confidence: 28,
        explanation:
          "The available trusted sources do not contain enough relevant evidence to confirm or reject this claim. Treat it cautiously until a reliable primary source or independent reporting becomes available.",
        sources: [],
      },
    ];

    function renderResult(result) {
      const verdictSymbols = {
        True: "✅",
        False: "❌",
        Misleading: "⚠️",
        Satire: "🎭",
        Unverified: "🔎",
      };
      const confidenceLabel = result.confidence >= 70
        ? "HIGH"
        : result.confidence >= 40
          ? "MODERATE"
          : "LOW";
      verdictElement.textContent = `${verdictSymbols[result.verdict] || "🔎"} ${result.verdict.toUpperCase()}`;
      confidenceElement.textContent = `Confidence: ${confidenceLabel} (${result.confidence}%)`;
      explanationElement.textContent = result.explanation;
      sourcesElement.replaceChildren();
      for (const source of (result.sources || []).slice(0, 5)) {
        const sourceLink = document.createElement("a");
        sourceLink.textContent = `🔗 ${source.title || source.url}`;
        sourceLink.href = source.url;
        sourceLink.target = "_blank";
        sourceLink.rel = "noreferrer";
        sourcesElement.append(sourceLink);
      }
      sourcesHeading.hidden = !(result.sources || []).length;
    }

    function positionPanel() {
      const badgeRect = badge.getBoundingClientRect();
      const panelWidth = panel.offsetWidth;
      const panelHeight = panel.offsetHeight;
      const left = Math.max(
        8,
        Math.min(window.innerWidth - panelWidth - 8, badgeRect.right - panelWidth),
      );
      const fitsAbove = badgeRect.top >= panelHeight + 16;
      const preferredTop = fitsAbove ? badgeRect.top - 8 : badgeRect.bottom + 8;
      const top = Math.max(
        8,
        Math.min(window.innerHeight - panelHeight - 8, preferredTop),
      );
      panel.style.left = `${left}px`;
      panel.style.top = `${top}px`;
      panel.style.transform = fitsAbove ? "translateY(-100%)" : "none";
    }

    function positionBadge() {
      const postRect = post.getBoundingClientRect();
      badge.style.left = `${postRect.right}px`;
      badge.style.top = `${postRect.top + 8}px`;
    }

    function showPanel() {
      panel.hidden = false;
      post.classList.add("trustlens-post-active");
      positionPanel();
    }

    function hidePanel() {
      if (!panelPinned) {
        panel.hidden = true;
        post.classList.remove("trustlens-post-active");
      }
    }

    function closePanel() {
      panelPinned = false;
      panel.hidden = true;
      post.classList.remove("trustlens-post-active");
    }

    function confidenceClass(confidence) {
      if (confidence >= 70) return "high";
      if (confidence >= 40) return "medium";
      return "low";
    }

    badge.addEventListener("mouseleave", () => {
      if (!panelPinned && !panel.matches(":hover")) {
        hidePanel();
      }
    }, { signal: listenerController.signal });

    badge.addEventListener("click", () => {
      if (panelPinned) {
        closePanel();
        return;
      }
      panelPinned = true;
      showPanel();
      requestVerdict();
    }, { signal: listenerController.signal });

    panel.addEventListener("mouseleave", () => {
      hidePanel();
    }, { signal: listenerController.signal });

    document.addEventListener("click", (event) => {
      if (!panel.hidden && !panel.contains(event.target) && !badge.contains(event.target)) {
        closePanel();
      }
    }, { capture: true, signal: listenerController.signal });

    overlayLayer.append(badge);
    positionBadge();
    document.body.append(panel);
    window.addEventListener("scroll", () => {
      positionBadge();
      if (!panel.hidden) {
        const badgeRect = badge.getBoundingClientRect();
        if (
          badgeRect.bottom <= 0
          || badgeRect.top >= window.innerHeight
          || badgeRect.right <= 0
          || badgeRect.left >= window.innerWidth
        ) {
          closePanel();
        } else {
          positionPanel();
        }
      }
    }, { passive: true, signal: listenerController.signal });
    document.addEventListener("scroll", () => {
      positionBadge();
      if (!panel.hidden) {
        const badgeRect = badge.getBoundingClientRect();
        if (
          badgeRect.bottom <= 0
          || badgeRect.top >= window.innerHeight
          || badgeRect.right <= 0
          || badgeRect.left >= window.innerWidth
        ) {
          closePanel();
        } else {
          positionPanel();
        }
      }
    }, { capture: true, passive: true, signal: listenerController.signal });
    window.addEventListener("resize", () => {
      positionBadge();
      if (!panel.hidden) {
        positionPanel();
      }
    }, { signal: listenerController.signal });
    badgeByPost.set(post, badge);
    postCleanupHandlers.set(post, () => {
      listenerController.abort();
      badge.remove();
      panel.remove();
      post.classList.remove("trustlens-post-active");
      badgeByPost.delete(post);
      postCleanupHandlers.delete(post);
    });
  }

  function scanPosts() {
    document.querySelectorAll(postSelector).forEach(addBadge);
    for (const [post, cleanup] of postCleanupHandlers) {
      if (!document.body.contains(post)) {
        cleanup();
      }
    }
  }

  scanPosts();

  const observer = new MutationObserver(scanPosts);
  observer.observe(document.body, { childList: true, subtree: true });
})();
