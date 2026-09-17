import { useEffect, useState } from "react";
import "./App.css";

const API_BASE_URL = "http://localhost:8000";
const NOTIFICATION_POLL_INTERVAL_MS = 5 * 60 * 1000;

function App() {
  const [startDate, setStartDate] = useState("");
  const [endDate, setEndDate] = useState("");
  const [searched, setSearched] = useState(false);
  const [results, setResults] = useState([]);
  const [selectedNotification, setSelectedNotification] = useState(null);
  const [extractedData, setExtractedData] = useState(null);
  const [analysisData, setAnalysisData] = useState(null);
  const [activeTab, setActiveTab] = useState("Reason");
  const [unreadNotifications, setUnreadNotifications] = useState([]);
  const [modalNotifications, setModalNotifications] = useState([]);
  const [showNotificationModal, setShowNotificationModal] = useState(false);
  const [showNotificationPanel, setShowNotificationPanel] = useState(false);
  const [isCheckingNotifications, setIsCheckingNotifications] = useState(false);
  const [notificationCheckError, setNotificationCheckError] = useState("");
  const [lastChecked, setLastChecked] = useState(null);
  const [analysisError, setAnalysisError] = useState("");

  useEffect(() => {
    let isActive = true;

    const checkForNewNotifications = async () => {
      if (isActive) setIsCheckingNotifications(true);

      try {
        const response = await fetch(`${API_BASE_URL}/api/notifications/new`);

        if (!response.ok) {
          // A second development-mode React effect can overlap the first
          // request; the backend deliberately rejects that duplicate check.
          if (response.status === 429) return;
          throw new Error("Unable to check FSSAI notifications");
        }

        const data = await response.json();
        if (!isActive) return;

        const unread = data.notifications || [];
        const fresh = data.new_notifications || [];

        setUnreadNotifications(unread);
        setLastChecked(data.last_successful_check || null);
        setNotificationCheckError("");

        if (fresh.length > 0) {
          setModalNotifications(fresh);
          setShowNotificationModal(true);
        }
      } catch (error) {
        if (isActive) {
          console.error("Notification monitor error:", error);
          setNotificationCheckError("Unable to check FSSAI notifications.");
        }
      } finally {
        if (isActive) setIsCheckingNotifications(false);
      }
    };

    checkForNewNotifications();
    const intervalId = window.setInterval(
      checkForNewNotifications,
      NOTIFICATION_POLL_INTERVAL_MS
    );

    return () => {
      isActive = false;
      window.clearInterval(intervalId);
    };
  }, []);

  const markNotificationsRead = async (notifications) => {
    const notificationIds = notifications.map((notification) => notification.id);

    if (notificationIds.length === 0) return;

    try {
      await fetch(`${API_BASE_URL}/api/notifications/mark-read`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ notification_ids: notificationIds }),
      });
      setUnreadNotifications((current) =>
        current.filter((notification) => !notificationIds.includes(notification.id))
      );
    } catch (error) {
      console.error("Unable to mark notifications as read:", error);
    }
  };

  const showNewNotifications = async () => {
    setResults(modalNotifications);
    setSearched(true);
    setSelectedNotification(null);
    setExtractedData(null);
    setAnalysisData(null);
    setShowNotificationModal(false);
    await markNotificationsRead(modalNotifications);
  };

  const handleBellClick = async () => {
    setShowNotificationPanel((isOpen) => !isOpen);
  };

  const handleSearch = async () => {
  if (!startDate || !endDate) {
    alert("Please select both Start Date and End Date.");
    return;
  }

  if (startDate > endDate) {
    alert("Start Date cannot be after End Date.");
    return;
  }

  try {
    console.log(
      `Fetching notifications from ${startDate} to ${endDate}`
    );

    const [startYear, startMonth, startDay] = startDate.split("-");
    const [endYear, endMonth, endDay] = endDate.split("-");

    const formattedStartDate = `${startDay}-${startMonth}-${startYear}`;
    const formattedEndDate = `${endDay}-${endMonth}-${endYear}`;

    const response = await fetch(
      `${API_BASE_URL}/api/notifications?start_date=${formattedStartDate}&end_date=${formattedEndDate}`
  );

    if (!response.ok) {
      throw new Error("Failed to fetch notifications");
    }

    const data = await response.json();

    console.log("Notifications from backend:", data);

    setResults(data.notifications || []);
    setSearched(true);
    setSelectedNotification(null);
    setExtractedData(null);
    setAnalysisData(null);

  } catch (error) {
    console.error("Notification fetch error:", error);
    alert("Failed to fetch notifications. Please try again.");
  }
};


  const handleNotificationClick = async (notification) => {
  console.log("CLICKED NOTIFICATION:", notification);

  setSelectedNotification(notification);
  setActiveTab("Reason");
  setExtractedData(null);
  setAnalysisData(null);
  setAnalysisError("");

  try {
    // Get the extracted file name from the notification
    const extractedFile =
      notification.extracted_file ||
      notification.extracted_filename ||
      notification.filename;

    console.log("Extracted file:", extractedFile);

    if (!extractedFile) {
      setAnalysisError(
        "This official notification has not yet been processed into the local AI pipeline."
      );
      return;
    }

    // Get extracted notification data
    const response = await fetch(
      `${API_BASE_URL}/api/notification/${encodeURIComponent(
        extractedFile
      )}`
    );

    if (!response.ok) {
      throw new Error(
        `Failed to fetch extracted notification data: ${response.status}`
      );
    }

    const data = await response.json();

    console.log("Extracted JSON:", data);

    setExtractedData(data);

    // Get Gemini analysis
    const analysisResponse = await fetch(
      `${API_BASE_URL}/api/analyze-notification/${encodeURIComponent(
        extractedFile
      )}`
    );

    if (!analysisResponse.ok) {
      throw new Error(
        `Failed to analyze notification: ${analysisResponse.status}`
      );
    }

    const analysis = await analysisResponse.json();

    console.log("Gemini Analysis:", analysis);

    setAnalysisData(analysis);
  } catch (error) {
    console.error("Notification detail error:", error);
    setAnalysisError("Unable to load local extraction or AI analysis for this notification.");
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

        <div className="header-actions">
          {unreadNotifications.length > 0 && (
            <div
              className="notification-marquee"
              title="New FSSAI Gazette notifications"
            >
              <div className="notification-marquee-track">
                {[...unreadNotifications.slice(0, 3), ...unreadNotifications.slice(0, 3)].map(
                  (notification, index) => (
                    <span key={`${notification.id}-${index}`}>
                      <strong>NEW:</strong> {notification.title} · {notification.uploaded_date}
                    </span>
                  )
                )}
              </div>
            </div>
          )}

          <div className="notification-monitor">
            <button
              type="button"
              className="notification-bell"
              onClick={handleBellClick}
              aria-label="Open new Gazette notifications"
              aria-expanded={showNotificationPanel}
            >
              <span aria-hidden="true">🔔</span>
              {unreadNotifications.length > 0 && (
                <span className="notification-badge">{unreadNotifications.length}</span>
              )}
            </button>

            {showNotificationPanel && (
              <div className="notification-dropdown">
                <p className="notification-dropdown-title">NEW GAZETTE NOTIFICATIONS</p>
                {unreadNotifications.length > 0 ? (
                  unreadNotifications.map((notification) => (
                    <button
                      type="button"
                      className="notification-dropdown-item"
                      key={notification.id}
                      onClick={() => {
                        setResults([notification]);
                        setSearched(true);
                        setShowNotificationPanel(false);
                        markNotificationsRead([notification]);
                        handleNotificationClick(notification);
                      }}
                    >
                      <strong>{notification.title}</strong>
                      <span>{notification.uploaded_date}</span>
                    </button>
                  ))
                ) : (
                  <p className="notification-dropdown-empty">No new Gazette notifications.</p>
                )}
              </div>
            )}
          </div>

          <div className="status-badge">
            <span className="status-dot"></span>
            System Ready
          </div>
        </div>
      </header>

      <div className="notification-check-status" aria-live="polite">
        {isCheckingNotifications
          ? "Checking for new notifications..."
          : notificationCheckError
            ? notificationCheckError
            : lastChecked
              ? `✓ Last checked: ${new Date(lastChecked).toLocaleTimeString([], { hour: "numeric", minute: "2-digit" })}`
              : ""}
      </div>

      {showNotificationModal && (
        <div className="notification-modal-backdrop" role="presentation">
          <section className="notification-modal" role="dialog" aria-modal="true" aria-labelledby="new-notification-title">
            <div className="notification-modal-icon" aria-hidden="true">🔔</div>
            <p className="section-label">FSSAI MONITOR</p>
            <h2 id="new-notification-title">New Gazette Notification{modalNotifications.length === 1 ? "" : "s"}</h2>
            <p>
              New FSSAI Gazette notifications are available. {modalNotifications.length} new
              {modalNotifications.length === 1 ? " notification" : " notifications"} found.
            </p>
            <div className="notification-modal-actions">
              <button type="button" className="modal-primary-button" onClick={showNewNotifications}>
                View Notifications
              </button>
              <button type="button" className="modal-secondary-button" onClick={() => setShowNotificationModal(false)}>
                Later
              </button>
            </div>
          </section>
        </div>
      )}

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

                <p>
                  Search a date range to view Gazette Notifications.
                </p>
              </div>
            )}

            {searched && results.length === 0 && (
              <div className="empty-results">
                <div className="empty-results-icon">🔍</div>

                <p>
                  No Gazette Notifications were found in this date range.
                </p>
              </div>
            )}

            {results.length > 0 && (
              <div className="notification-list">
                {results.map((notification,index) => (
                  <button
                    key={notification.id || index}
                    className={`notification-card notification-card-${
                      notification.id
                    } ${
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

            </div>
          ) : (

            <div className="notification-details">

              {/* SELECTED NOTIFICATION HEADER */}

              <div className="selected-notification-header">

                <p className="selected-label">
                  SELECTED NOTIFICATION #{selectedNotification.id}
                </p>

                <h3>{selectedNotification.title}</h3>

                <div className="notification-meta">
                  <span>
                    📅 {selectedNotification.uploaded_date}
                  </span>
                </div>

              </div>

              {/* NOTIFICATION DETAILS */}

              <div className="details-grid">

                <div className="detail-card">
                  <p className="detail-label">
                    NOTIFICATION DATE
                  </p>

                  <h4>
                    {selectedNotification.uploaded_date}
                  </h4>
                </div>

                <div className="detail-card">
                  <p className="detail-label">
                    NOTIFICATION TYPE
                  </p>

                  <h4>
                    Gazette Notification
                  </h4>
                </div>

              </div>

              {/* SOURCE DOCUMENT */}

              <div className="source-file-section">

                <p className="detail-label">
                  SOURCE DOCUMENT
                </p>

                <a
                  href={selectedNotification.pdf_url}
                  target="_blank"
                  rel="noreferrer"
                  className="pdf-link"
                >
                  Open Original Gazette PDF ↗
                </a>

              </div>

              {/* EXTRACTED DOCUMENT */}

              {extractedData && (
                <div className="extracted-preview">

                  <p className="detail-label">
                    EXTRACTED DOCUMENT DATA
                  </p>

                  <p>
                    <strong>File:</strong>{" "}
                    {extractedData.file_name}
                  </p>

                  <p>
                    <strong>Pages:</strong>{" "}
                    {extractedData.page_count}
                  </p>

                  <p>
                    <strong>Extracted Text Preview:</strong>
                  </p>

                  <div className="extracted-text-preview">
                    {extractedData.text.slice(0, 1000)}
                  </div>

                </div>
              )}

              {/* AI ANALYSIS TABS */}

              <div className="analysis-features">

                {[
                  "Reason",
                  "Regulations",
                  "Areas Affected",
                  "Source Files",
                ].map((tab) => (
                  <button
                    key={tab}
                    className={
                      activeTab === tab
                        ? "active-tab"
                        : ""
                    }
                    onClick={() => setActiveTab(tab)}
                  >
                    {tab}
                  </button>
                ))}

              </div>

              {/* AI ANALYSIS CONTENT */}

              <div className="analysis-content">

                {/* REASON */}

                {activeTab === "Reason" && (
                  <div>

                    <h4>Reason</h4>

                    {analysisData ? (
                      <p>
                        {analysisData.reason}
                      </p>
                    ) : analysisError ? (
                      <p>{analysisError}</p>
                    ) : (
                      <p>
                        Loading notification analysis...
                      </p>
                    )}

                  </div>
                )}

                {/* REGULATIONS */}
{activeTab === "Regulations" && (
  <div>

    <h4>Regulations</h4>

    {analysisData ? (
      <div className="regulations-list">

        {analysisData.regulations?.map(
          (regulation, index) => (
            <div className="regulation-card" key={index}>

              <p>
                <strong>Title:</strong>{" "}
                {regulation.title || "Not specified"}
              </p>

              <p>
                <strong>Section:</strong>{" "}
                {regulation.section || "Not available"}
              </p>

              <p>
                <strong>Subsection:</strong>{" "}
                {regulation.subsection || "Not available"}
              </p>

              <p>
                <strong>Change:</strong>{" "}
                {regulation.change || "Not specified"}
              </p>

              <p>
                <strong>PDF Name:</strong>{" "}
                {regulation.pdf_name || "Not available"}
              </p>

              {regulation.pdf_link && (
                <p>
                  <strong>Source:</strong>{" "}
                  <a
                    href={regulation.pdf_link}
                    target="_blank"
                    rel="noopener noreferrer"
                  >
                    View PDF
                  </a>
                </p>
              )}

            </div>
          )
        )}

      </div>
    ) : (
      <p>
        Loading notification analysis...
      </p>
    )}

  </div>
)}
{/* AREAS AFFECTED */}

{activeTab === "Areas Affected" && (
  <div>

    <h4>Areas Affected</h4>

    {analysisData ? (
      <div className="affected-areas-list">

        {analysisData.affected_areas?.map(
          (area, index) => (
            <div className="affected-area-card" key={index}>

              <p>
                <strong>Section:</strong>{" "}
                {area.section_code || "Not specified"}
              </p>

              <p>
                <strong>Section Title:</strong>{" "}
                {area.section_title || "Not specified"}
              </p>

              <p>
                <strong>Subsection:</strong>{" "}
                {area.subsection || "Not specified"}
              </p>

              <p>
                <strong>Description:</strong>{" "}
                {area.description || "Not specified"}
              </p>

            </div>
          )
        )}

      </div>
    ) : (
      <p>
        Loading notification analysis...
      </p>
    )}

  </div>
)}

                {/* SOURCE FILES */}

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
                      <>
                        <p>
                          <strong>Extracted file:</strong>{" "}
                          {extractedData.file_name}
                        </p>

                        <p>
                          <strong>Pages:</strong>{" "}
                          {extractedData.page_count}
                        </p>
                      </>
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
