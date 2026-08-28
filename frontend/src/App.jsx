import { useState } from "react";
import "./App.css";
import { notifications } from "./data/notifications";

function App() {
  const [startDate, setStartDate] = useState("");
  const [endDate, setEndDate] = useState("");
  const [searched, setSearched] = useState(false);
  const [results, setResults] = useState([]);
  const [selectedNotification, setSelectedNotification] = useState(null);
  const [extractedData, setExtractedData] = useState(null);
  const [activeTab, setActiveTab] = useState("Reason");
  const handleSearch = () => {
    if (!startDate || !endDate) {
      alert("Please select both Start Date and End Date.");
      return;
    }

    const filteredNotifications = notifications.filter((notification) => {
      const [day, month, year] = notification.uploaded_date.split("-");

      const notificationDate = new Date(
        `${year}-${month}-${day}T00:00:00`
      );

      const selectedStartDate = new Date(`${startDate}T00:00:00`);
      const selectedEndDate = new Date(`${endDate}T23:59:59`);

      return (
        notificationDate >= selectedStartDate &&
        notificationDate <= selectedEndDate
      );
    });

    setResults(filteredNotifications);
    setSearched(true);
    setSelectedNotification(null);
  };
  const handleNotificationClick = async (notification) => {
  setSelectedNotification(notification);
  setExtractedData(null);
  setActiveTab("Reason");

  try {
    const response = await fetch(
      `http://127.0.0.1:8000/api/notification/${encodeURIComponent(
        notification.extracted_file
      )}`
    );

    if (!response.ok) {
      throw new Error("Failed to fetch extracted notification data");
    }

    const data = await response.json();

    console.log("Extracted JSON:", data);

    setExtractedData(data);
  } catch (error) {
    console.error(error);
  }
};

  return (
    <div className="app">
      <header className="header">
        <div>
          <p className="eyebrow">REGULATORY INTELLIGENCE PLATFORM</p>

          <h1>FSSAI Gazette Notification System</h1>

          <p className="subtitle">
            Search, analyze and explore Gazette Notifications through a unified
            regulatory intelligence dashboard.
          </p>
        </div>

        <div className="status-badge">
          <span className="status-dot"></span>
          System Ready
        </div>
      </header>

      <main className="dashboard">
        {/* LEFT SIDE - SEARCH AGENT */}

        <section className="search-panel">
          <div className="panel-heading">
            <div>
              <p className="section-label">SEARCH AGENT</p>
              <h2>Find Gazette Notifications</h2>
            </div>

            <div className="agent-icon">⌕</div>
          </div>

          <p className="panel-description">
            Select a date range to retrieve relevant FSSAI Gazette Notifications.
          </p>

          <div className="date-grid">
            <div className="input-group">
              <label>Start Date</label>

              <input
                type="date"
                value={startDate}
                onChange={(e) => setStartDate(e.target.value)}
              />
            </div>

            <div className="input-group">
              <label>End Date</label>

              <input
                type="date"
                value={endDate}
                onChange={(e) => setEndDate(e.target.value)}
              />
            </div>
          </div>

          <button className="search-button" onClick={handleSearch}>
            Search Notifications
          </button>

          <div className="results-section">
            <div className="results-header">
              <div>
                <p className="section-label">RESULTS</p>

                <h3>
                  {!searched
                    ? "Ready to search"
                    : results.length > 0
                    ? "Notifications Found"
                    : "No Notifications Found"}
                </h3>
              </div>

              <span className="result-count">{results.length}</span>
            </div>

            {!searched && (
              <div className="empty-results">
                <div className="empty-results-icon">📄</div>

                <p>Search a date range to view Gazette Notifications.</p>
              </div>
            )}

            {searched && results.length === 0 && (
              <div className="empty-results">
                <div className="empty-results-icon">🔍</div>

                <p>No Gazette Notifications were found in this date range.</p>
              </div>
            )}

            {results.length > 0 && (
              <div className="notification-list">
                {results.map((notification) => (
                  <button
                    key={notification.id}
                    className={`notification-card ${
                      selectedNotification?.id === notification.id
                        ? "selected-notification"
                        : ""
                    }`}
                    onClick={() => handleNotificationClick(notification)}
                  >
                    <div className="notification-card-top">
                      <span className="notification-number">
                        #{notification.id}
                      </span>

                      <span className="notification-date">
                        {notification.uploaded_date}
                      </span>
                    </div>

                    <h4>{notification.title}</h4>

                    <span className="view-details">
                      View notification details →
                    </span>
                  </button>
                ))}
              </div>
            )}
          </div>
        </section>

        {/* RIGHT SIDE - AI ANALYSIS */}

        {/* RIGHT SIDE - AI ANALYSIS */}

{/* RIGHT SIDE - AI ANALYSIS */}

<section className="analysis-panel">
  <div className="panel-heading">
    <div>
      <p className="section-label">AI REGULATORY ANALYSIS</p>
      <h2>Notification Intelligence</h2>
    </div>

    <div className="ai-badge">AI</div>
  </div>

  {!selectedNotification ? (
    <div className="analysis-empty-state">
      <div className="robot-wrapper">
        <div className="robot">
          <div className="robot-antenna"></div>

          <div className="robot-head">
            <span className="eye"></span>
            <span className="eye"></span>
          </div>

          <div className="robot-body">
            <span></span>
          </div>
        </div>
      </div>

      <h3>Your AI analysis workspace is ready</h3>

      <p>
        Select a Gazette Notification from the search results to view
        extracted information, affected regulations, key dates, reason,
        areas affected and source documents.
      </p>

      <div className="analysis-tabs">
  <button
    className={activeTab === "reason" ? "active-tab" : ""}
    onClick={() => setActiveTab("reason")}
  >
    Reason
  </button>

  <button
    className={activeTab === "regulations" ? "active-tab" : ""}
    onClick={() => setActiveTab("regulations")}
  >
    Regulations
  </button>

  <button
    className={activeTab === "areas" ? "active-tab" : ""}
    onClick={() => setActiveTab("areas")}
  >
    Areas Affected
  </button>

  <button
    className={activeTab === "source" ? "active-tab" : ""}
    onClick={() => setActiveTab("source")}
  >
    Source Files
  </button>
</div>

<div className="tab-content">
  {activeTab === "reason" && (
    <div>
      <h4>Reason</h4>
      <p>
        AI analysis of the reason behind this Gazette Notification will appear here.
      </p>
    </div>
  )}

  {activeTab === "regulations" && (
    <div>
      <h4>Regulations</h4>
      <p>
        Relevant regulations and sections identified from the document will appear here.
      </p>
    </div>
  )}

  {activeTab === "areas" && (
    <div>
      <h4>Areas Affected</h4>
      <p>
        Areas, industries and stakeholders affected by this notification will appear here.
      </p>
    </div>
  )}

  {activeTab === "source" && (
    <div>
      <h4>Source Files</h4>

      <a
        href={selectedNotification.pdf_url}
        target="_blank"
        rel="noreferrer"
      >
        Open Original Gazette PDF
      </a>
    </div>
  )}
</div>
    </div>
  ) : (
    <div className="notification-details">

      <div className="selected-notification-header">
        <p className="selected-label">
          SELECTED NOTIFICATION #{selectedNotification.id}
        </p>

        <h3>{selectedNotification.title}</h3>

        <div className="notification-meta">
          <span>📅 {selectedNotification.uploaded_date}</span>
        </div>
      </div>

      <div className="details-grid">
        <div className="detail-card">
          <p className="detail-label">NOTIFICATION DATE</p>
          <h4>{selectedNotification.uploaded_date}</h4>
        </div>

        <div className="detail-card">
          <p className="detail-label">NOTIFICATION TYPE</p>
          <h4>Gazette Notification</h4>
        </div>
      </div>

      <div className="source-file-section">
        <p className="detail-label">SOURCE DOCUMENT</p>

        <a
          href={selectedNotification.pdf_url}
          target="_blank"
          rel="noreferrer"
          className="pdf-link"
        >
          Open Original Gazette PDF ↗
        </a>
      </div>

      {extractedData && (
        <div className="extracted-preview">
          <p className="detail-label">EXTRACTED DOCUMENT DATA</p>

          <p>
            <strong>File:</strong> {extractedData.file_name}
          </p>

          <p>
            <strong>Pages:</strong> {extractedData.page_count}
          </p>

          <p>
            <strong>Extracted Text Preview:</strong>
          </p>

          <div className="extracted-text-preview">
            {extractedData.text.slice(0, 1000)}
          </div>
        </div>
      )}

      <div className="analysis-features">
        {["Reason", "Regulations", "Areas Affected", "Source Files"].map(
          (tab) => (
            <button
              key={tab}
              className={activeTab === tab ? "active-tab" : ""}
              onClick={() => setActiveTab(tab)}
            >
              {tab}
            </button>
          )
        )}
      </div>

      <div className="analysis-content">

        {activeTab === "Reason" && (
          <div>
            <h4>Reason</h4>
            <p>
              AI analysis of the reason behind this Gazette Notification will
              appear here.
            </p>
          </div>
        )}

        {activeTab === "Regulations" && (
          <div>
            <h4>Regulations</h4>
            <p>
              Relevant FSSAI regulations, sections and legal provisions will
              appear here.
            </p>
          </div>
        )}

        {activeTab === "Areas Affected" && (
          <div>
            <h4>Areas Affected</h4>
            <p>
              The industries, laboratories, food businesses or other
              stakeholders affected by this notification will appear here.
            </p>
          </div>
        )}

        {activeTab === "Source Files" && (
          <div>
            <h4>Source Files</h4>

            <p>
              <strong>Original PDF:</strong>{" "}
              <a
                href={selectedNotification.pdf_url}
                target="_blank"
                rel="noreferrer"
              >
                Open Gazette PDF
              </a>
            </p>

            {extractedData && (
              <p>
                <strong>Extracted file:</strong>{" "}
                {extractedData.file_name}
              </p>
            )}
          </div>
        )}

      </div>

    </div>
  )}
</section>
      </main>
    </div>
  );
}
export default App;