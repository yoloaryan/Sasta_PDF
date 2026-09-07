const API_URL = (window.location.hostname === "localhost" || window.location.hostname === "127.0.0.1")
  ? `http://${window.location.hostname}:8000`
  : "http://127.0.0.1:8000";

const MAX_FILE_SIZE_BYTES = 10 * 1024 * 1024; // 10 MB limit
let isUploading = false;

let documents = [];
let selectedDocument = null;

// Global helper functions for inline HTML event handlers
window.switchNavTab = function (tab) {
  const navHome = document.getElementById("navHome");
  const navDocuments = document.getElementById("navDocuments");
  const navAIAssistant = document.getElementById("navAIAssistant");
  const workspace = document.querySelector(".workspace");

  [navHome, navDocuments, navAIAssistant].forEach(btn => {
    if (btn) btn.classList.remove("active");
  });

  if (workspace) {
    workspace.classList.remove("view-mode-home", "view-mode-documents", "view-mode-ai");
  }

  if (tab === "home") {
    if (navHome) navHome.classList.add("active");
    if (workspace) workspace.classList.add("view-mode-home");
  } else if (tab === "documents") {
    if (navDocuments) navDocuments.classList.add("active");
    if (workspace) workspace.classList.add("view-mode-documents");
  } else if (tab === "ai") {
    if (navAIAssistant) navAIAssistant.classList.add("active");
    if (workspace) workspace.classList.add("view-mode-ai");
    const questionInput = document.getElementById("questionInput");
    if (questionInput) questionInput.focus();
  }
};

window.openUploader = function () {
  if (isUploading) {
    alert("A PDF upload is currently in progress. Please wait for it to complete.");
    return;
  }
  const fileInput = document.getElementById("fileInput");
  if (fileInput) {
    fileInput.value = "";
    fileInput.click();
  }
};

window.askSuggestion = function (question) {
  const questionInput = document.getElementById("questionInput");
  if (questionInput) {
    questionInput.value = question;
    window.sendQuestion();
  }
};

window.sendQuestion = async function () {
  const questionInput = document.getElementById("questionInput");
  const question = questionInput ? questionInput.value.trim() : "";

  if (!question) return;

  if (!selectedDocument) {
    addAIMessage(
      "Please upload and select a PDF before asking a question."
    );
    return;
  }

  addUserMessage(question);
  if (questionInput) questionInput.value = "";

  const loadingId = addAILoading();

  try {
    const response = await fetch(`${API_URL}/chat`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json"
      },
      body: JSON.stringify({
        question,
        document_id: selectedDocument.document_id
      })
    });

    const data = await response.json();

    removeMessage(loadingId);

    if (!response.ok) {
      throw new Error(data.detail || "Chat request failed.");
    }

    addAIMessage(
      formatAnswer(data.answer, data.sources)
    );

  } catch (error) {
    removeMessage(loadingId);

    addAIMessage(
      `Sorry, something went wrong.<br><br>
       ${escapeHTML(error.message)}`
    );
  }
};

window.deleteDocument = async function (documentId, event) {
  if (event) event.stopPropagation();

  const doc = documents.find(d => d.document_id === documentId);
  if (!doc) return;

  if (!confirm(`Are you sure you want to delete "${doc.filename}"?`)) {
    return;
  }

  try {
    const response = await fetch(
      `${API_URL}/documents/${encodeURIComponent(doc.document_id)}?filename=${encodeURIComponent(doc.filename)}`,
      { method: "DELETE" }
    );

    const data = await response.json();

    if (!response.ok) {
      throw new Error(data.detail || "Failed to delete document on server.");
    }

    documents = documents.filter(d => d.document_id !== doc.document_id);

    if (selectedDocument && selectedDocument.document_id === doc.document_id) {
      selectedDocument = null;
      const currentDocument = document.getElementById("currentDocument");
      const selectedDocumentName = document.getElementById("selectedDocumentName");
      const welcomeDocument = document.getElementById("welcomeDocument");
      const pdfFrame = document.getElementById("pdfFrame");

      if (currentDocument) {
        currentDocument.innerHTML = `<span class="pdf-small-icon">PDF</span> No document selected`;
      }
      if (selectedDocumentName) {
        selectedDocumentName.textContent = "None";
      }
      if (welcomeDocument) welcomeDocument.hidden = false;
      if (pdfFrame) {
        pdfFrame.hidden = true;
        pdfFrame.src = "";
      }
    }

    renderDocumentList();
    addAIMessage(`🗑️ Document <b>${escapeHTML(doc.filename)}</b> has been deleted.`);

  } catch (error) {
    console.error("Delete error:", error);
    alert(`Delete Failed: ${error.message}`);
  }
};

// Initialize event listeners when DOM content is loaded
document.addEventListener("DOMContentLoaded", () => {
  const uploadButton = document.getElementById("uploadButton");
  const welcomeUploadButton = document.getElementById("welcomeUploadButton");
  const fileInput = document.getElementById("fileInput");
  const questionInput = document.getElementById("questionInput");
  const themeToggle = document.getElementById("themeToggle");

  if (fileInput) {
    fileInput.multiple = false;
  }

  // Dark Mode Management
  function initTheme() {
    const savedTheme = localStorage.getItem("sastapdf_theme") || "dark";
    setTheme(savedTheme);
  }

  function setTheme(theme) {
    document.documentElement.setAttribute("data-theme", theme);
    localStorage.setItem("sastapdf_theme", theme);
    if (themeToggle) {
      themeToggle.textContent = theme === "dark" ? "☀️" : "🌙";
      themeToggle.setAttribute(
        "title",
        `Switch to ${theme === "dark" ? "Light" : "Dark"} Mode`
      );
    }
  }

  if (themeToggle) {
    themeToggle.addEventListener("click", () => {
      const currentTheme = document.documentElement.getAttribute("data-theme") || "light";
      const nextTheme = currentTheme === "dark" ? "light" : "dark";
      setTheme(nextTheme);
    });
  }

  initTheme();

  // Toolbar Actions (Zoom & Fullscreen)
  let currentZoom = 100;
  const btnZoomIn = document.getElementById("btnZoomIn");
  const btnZoomOut = document.getElementById("btnZoomOut");
  const btnZoomReset = document.getElementById("btnZoomReset");
  const btnFullscreen = document.getElementById("btnFullscreen");
  const zoomLevelText = document.getElementById("zoomLevelText");

  function updateZoom(delta) {
    if (delta === 0) {
      currentZoom = 100;
    } else {
      currentZoom = Math.min(Math.max(currentZoom + delta, 50), 250);
    }
    if (zoomLevelText) zoomLevelText.textContent = `${currentZoom}%`;

    const pdfFrame = document.getElementById("pdfFrame");
    if (pdfFrame) {
      pdfFrame.style.transformOrigin = "top center";
      pdfFrame.style.transform = `scale(${currentZoom / 100})`;
      pdfFrame.style.transition = "transform 0.2s ease";
    }
  }

  if (btnZoomIn) btnZoomIn.addEventListener("click", () => updateZoom(25));
  if (btnZoomOut) btnZoomOut.addEventListener("click", () => updateZoom(-25));
  if (btnZoomReset) btnZoomReset.addEventListener("click", () => updateZoom(0));

  if (btnFullscreen) {
    btnFullscreen.addEventListener("click", () => {
      const pdfViewer = document.getElementById("pdfViewer");
      if (!pdfViewer) return;

      if (!document.fullscreenElement) {
        if (pdfViewer.requestFullscreen) {
          pdfViewer.requestFullscreen();
        } else if (pdfViewer.webkitRequestFullscreen) {
          pdfViewer.webkitRequestFullscreen();
        }
      } else {
        if (document.exitFullscreen) {
          document.exitFullscreen();
        }
      }
    });
  }

  if (uploadButton) {
    uploadButton.addEventListener("click", window.openUploader);
  }

  if (welcomeUploadButton) {
    welcomeUploadButton.addEventListener("click", window.openUploader);
  }

  if (fileInput) {
    fileInput.addEventListener("change", async function () {
      if (!this.files || !this.files.length) return;

      const file = this.files[0];

      if (!file.name.toLowerCase().endsWith(".pdf")) {
        alert("Please select a valid PDF file (.pdf).");
        return;
      }

      // Check 10MB size limit
      if (file.size > MAX_FILE_SIZE_BYTES) {
        alert(`File size exceeds the 10MB limit (File size: ${(file.size / (1024 * 1024)).toFixed(2)} MB).`);
        this.value = "";
        return;
      }

      await uploadPDF(file);
    });
  }

  if (questionInput) {
    questionInput.addEventListener("keydown", event => {
      if (event.key === "Enter" && !event.shiftKey) {
        event.preventDefault();
        window.sendQuestion();
      }
    });

    questionInput.addEventListener("input", () => {
      questionInput.style.height = "auto";
      questionInput.style.height =
        Math.min(questionInput.scrollHeight, 100) + "px";
    });
  }

  renderDocumentList();
});

async function uploadPDF(file) {
  const fileInput = document.getElementById("fileInput");
  const formData = new FormData();
  formData.append("file", file);

  isUploading = true;
  setUploadLoading(true);

  try {
    const response = await fetch(`${API_URL}/upload`, {
      method: "POST",
      body: formData
    });

    const data = await response.json();

    if (!response.ok) {
      throw new Error(data.detail || "PDF processing failed on server.");
    }

    const existingIndex = documents.findIndex(
      d => d.filename === data.filename
    );

    if (existingIndex >= 0) {
      documents[existingIndex] = data;
    } else {
      documents.push(data);
    }

    renderDocumentList();
    selectDocument(data);

    let msg = `Document processed successfully.<br><br>
       <b>📄 ${escapeHTML(data.filename)}</b><br><br>
       📖 ${data.pages} pages &nbsp;|&nbsp; 🧩 ${data.chunks} chunks<br><br>`;

    if (data.warning) {
      msg += `⚠️ <i>${escapeHTML(data.warning)}</i><br><br>`;
    } else {
      msg += `Your document is indexed and ready! Ask any question below.`;
    }

    addAIMessage(msg);

  } catch (error) {
    console.error("Upload error:", error);
    alert(`Upload Failed: ${error.message}`);
    addAIMessage(
      `❌ <b>PDF Upload Failed</b><br><br>
       Reason: ${escapeHTML(error.message)}<br><br>
       Make sure the backend server is active at <code>${API_URL}</code>.`
    );
  } finally {
    isUploading = false;
    setUploadLoading(false);
    if (fileInput) fileInput.value = "";
  }
}

function setUploadLoading(loading) {
  const uploadButton = document.getElementById("uploadButton");
  const welcomeUploadButton = document.getElementById("welcomeUploadButton");

  if (uploadButton) {
    uploadButton.disabled = loading;
    uploadButton.innerHTML = loading
      ? "⏳ Processing PDF..."
      : '<span class="plus">+</span> Upload PDF';
  }

  if (welcomeUploadButton) {
    welcomeUploadButton.disabled = loading;
    welcomeUploadButton.textContent = loading ? "⏳ Processing PDF..." : "Upload a PDF";
  }
}

function renderDocumentList() {
  const documentList = document.getElementById("documentList");
  if (!documentList) return;

  if (!documents.length) {
    documentList.innerHTML =
      '<div class="empty-documents">' +
      '<div class="empty-icon">📄</div>' +
      '<span>No documents uploaded</span>' +
      '</div>';
    return;
  }

  documentList.innerHTML = "";

  documents.forEach(doc => {
    const item = document.createElement("div");

    item.className = "document-item";

    if (
      selectedDocument &&
      selectedDocument.document_id === doc.document_id
    ) {
      item.classList.add("active");
    }

    item.innerHTML =
      `<div class="document-item-icon">PDF</div>
       <div class="document-item-info">
         <span class="document-item-name">
           ${escapeHTML(doc.filename)}
         </span>
         <span class="document-item-meta">
           ${doc.pages} pages (${doc.chunks} chunks)
         </span>
       </div>
       <div class="document-item-actions">
         <button class="delete-doc-btn" onclick="deleteDocument('${doc.document_id}', event)" title="Delete PDF">
           🗑️
         </button>
       </div>`;

    item.addEventListener("click", () => selectDocument(doc));

    documentList.appendChild(item);
  });
}

function selectDocument(doc) {
  selectedDocument = doc;

  const currentDocument = document.getElementById("currentDocument");
  const selectedDocumentName = document.getElementById("selectedDocumentName");
  const welcomeDocument = document.getElementById("welcomeDocument");
  const pdfFrame = document.getElementById("pdfFrame");

  if (currentDocument) {
    currentDocument.innerHTML =
      `<span class="pdf-small-icon">PDF</span>
       ${escapeHTML(doc.filename)}`;
  }

  if (selectedDocumentName) {
    selectedDocumentName.textContent = doc.filename;
  }

  renderDocumentList();

  if (welcomeDocument) welcomeDocument.hidden = true;
  if (pdfFrame) {
    pdfFrame.hidden = false;
    pdfFrame.src = `${API_URL}/files/${encodeURIComponent(doc.filename)}`;
  }
}

function formatAnswer(answer, sources) {
  let html = escapeHTML(answer)
    .replace(/\*\*(.*?)\*\*/g, "<strong>$1</strong>")
    .replace(/\n/g, "<br>");

  if (sources && sources.length) {
    html += `<div class="sources">
      <div class="sources-title">SOURCES</div>`;

    sources.forEach(source => {
      html +=
        `<div class="source">
          📄 ${escapeHTML(source.filename)}
          — Page ${source.page}
        </div>`;
    });

    html += "</div>";
  }

  return html;
}

function addUserMessage(message) {
  const chatContainer = document.getElementById("chatContainer");
  if (!chatContainer) return;

  const wrapper = document.createElement("div");

  wrapper.className = "message user";

  wrapper.innerHTML =
    `<div class="message-content">
       ${escapeHTML(message)}
     </div>`;

  chatContainer.appendChild(wrapper);
  scrollChat();
}

function addAIMessage(message) {
  const chatContainer = document.getElementById("chatContainer");
  if (!chatContainer) return;

  const welcome = chatContainer.querySelector(".welcome-ai");

  if (welcome) welcome.remove();

  const wrapper = document.createElement("div");

  wrapper.className = "message";

  wrapper.innerHTML =
    `<img src="avatar.png" class="ai-msg-avatar" alt="AI Avatar">
     <div class="message-content">
       ${message}
     </div>`;

  chatContainer.appendChild(wrapper);
  scrollChat();
}

function addAILoading() {
  const chatContainer = document.getElementById("chatContainer");
  if (!chatContainer) return "";

  const id = "loading-" + Date.now();

  const wrapper = document.createElement("div");

  wrapper.id = id;
  wrapper.className = "message";

  wrapper.innerHTML =
    `<img src="avatar.png" class="ai-msg-avatar" alt="AI Avatar">
     <div class="message-content">
       Thinking...
     </div>`;

  chatContainer.appendChild(wrapper);
  scrollChat();

  return id;
}

function removeMessage(id) {
  const element = document.getElementById(id);

  if (element) {
    element.remove();
  }
}

function scrollChat() {
  const chatContainer = document.getElementById("chatContainer");
  if (chatContainer) {
    chatContainer.scrollTop = chatContainer.scrollHeight;
  }
}

function escapeHTML(value) {
  const div = document.createElement("div");
  div.textContent = String(value);
  return div.innerHTML;
}
