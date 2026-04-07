"use client";

import { ReactNode, useState } from "react";

interface TabSpec {
  id: string;
  label: string;
}

interface SectionTabsProps {
  tabs: TabSpec[];
  render: (tabId: string) => ReactNode;
}

export default function SectionTabs({ tabs, render }: SectionTabsProps) {
  const [activeTab, setActiveTab] = useState(tabs[0]?.id ?? "");

  return (
    <div>
      <div className="mb-4 flex flex-wrap gap-2">
        {tabs.map((tab) => (
          <button
            key={tab.id}
            type="button"
            onClick={() => setActiveTab(tab.id)}
            className={`rounded-full px-3 py-1 text-xs transition ${
              activeTab === tab.id
                ? "bg-gold text-[#1e140d]"
                : "border border-gold/25 bg-[#10203a] text-[#d7c8a5] hover:border-gold/40"
            }`}
          >
            {tab.label}
          </button>
        ))}
      </div>
      <div>{render(activeTab)}</div>
    </div>
  );
}
