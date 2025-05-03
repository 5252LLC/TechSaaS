import React from 'react';

/**
 * TabbedInterface component
 * 
 * @param {Object} props
 * @param {Array} props.tabs - Array of tab objects with id, title and optional icon
 * @param {string} props.activeTab - The ID of the currently active tab
 * @param {Function} props.onTabChange - Function to call when a tab is clicked
 * @param {React.ReactNode} props.children - Tab content components
 */
const TabbedInterface = ({ tabs, activeTab, onTabChange, children }) => {
  return (
    <div className="tabs-container">
      <div className="tabs">
        {tabs.map((tab) => (
          <button
            key={tab.id}
            className={`tab ${activeTab === tab.id ? 'active' : ''}`}
            onClick={() => onTabChange(tab.id)}
            data-tab={tab.id}
          >
            {tab.icon && <span className="tab-icon">{tab.icon}</span>}
            {tab.title}
          </button>
        ))}
      </div>
      
      <div className="tab-content">
        {children}
      </div>
    </div>
  );
};

export default TabbedInterface;
