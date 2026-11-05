// Initialize the Ionic glossary explorer and display all glossary cards A–Z.
import { initialize } from "@ionic/core/components";
import { defineCustomElement as defineIonApp } from "@ionic/core/components/ion-app.js";
import { defineCustomElement as defineIonContent } from "@ionic/core/components/ion-content.js";
import { defineCustomElement as defineIonHeader } from "@ionic/core/components/ion-header.js";
import { defineCustomElement as defineIonToolbar } from "@ionic/core/components/ion-toolbar.js";
import { defineCustomElement as defineIonTitle } from "@ionic/core/components/ion-title.js";
import { defineCustomElement as defineIonButton } from "@ionic/core/components/ion-button.js";
import { defineCustomElement as defineIonButtons } from "@ionic/core/components/ion-buttons.js";
import { defineCustomElement as defineIonFab } from "@ionic/core/components/ion-fab.js";
import { defineCustomElement as defineIonFabButton } from "@ionic/core/components/ion-fab-button.js";
import { defineCustomElement as defineIonIcon } from "ionicons/components/ion-icon.js";
import { addIcons } from "ionicons";
import { arrowUpOutline, homeOutline } from "ionicons/icons";
import { defineCustomElement as defineIonGrid } from "@ionic/core/components/ion-grid.js";
import { defineCustomElement as defineIonRow } from "@ionic/core/components/ion-row.js";
import { defineCustomElement as defineIonCol } from "@ionic/core/components/ion-col.js";
import { defineCustomElement as defineIonSearchbar } from "@ionic/core/components/ion-searchbar.js";

import "@ionic/core/css/core.css";
import "@ionic/core/css/normalize.css";
import "@ionic/core/css/structure.css";
import "@ionic/core/css/typography.css";
import "@ionic/core/css/padding.css";
import "@ionic/core/css/display.css";
import "./css/style.css";
import "./css/lifecycle_filter.css";

import { FilteringFlow, FilterData } from "@filtering.js/filtering.js/ui";
import glossary from "../tools/outputs/glossary.json";
import { registerGlossaryCardComponents, renderGlossaryCard } from "./card/glossary_card.js";

initialize();
defineIonApp();
defineIonContent();
defineIonHeader();
defineIonToolbar();
defineIonTitle();
defineIonButton();
defineIonButtons();
defineIonFab();
defineIonFabButton();
defineIonIcon();
addIcons({ arrowUpOutline, homeOutline });
defineIonGrid();
defineIonRow();
defineIonCol();
defineIonSearchbar();
registerGlossaryCardComponents();

// Preserve the glossary's alphabetical order, including a 0–9 section if needed.
const entries = [...glossary.terms].sort((a, b) =>
  a.term.localeCompare(b.term, "en", { sensitivity: "base" })
);

const groups = new Map();
for (const entry of entries) {
  const first = entry.term.trim().charAt(0).toUpperCase();
  const letter = /^[A-Z]$/.test(first) ? first : "0–9";
  if (!groups.has(letter)) groups.set(letter, []);
  groups.get(letter).push(entry);
}

// The generator provides stable IDs in chapter order, independent of display labels.
const stageNames = new Map();
for (const entry of entries) {
  if (!Array.isArray(entry.stage_ids) || entry.stage_ids.length !== (entry.stages || []).length) {
    throw new Error(`HEY! Missing lifecycle IDs for ${entry.term}. Regenerate tools/outputs/glossary.json.`);
  }
  entry.stage_ids.forEach((id, position) => {
    stageNames.set(id, entry.stages[position]);
  });
}
const stageIds = [...stageNames.keys()].sort(
  (a, b) => Number(a.slice(3)) - Number(b.slice(3))
);

// The header matches the handbook's Material indigo.
document.querySelector("#app").innerHTML = `
  <ion-app>
    <ion-header>
      <ion-toolbar style="--background: #4051B5; --color: white;">
        <!-- The handbook home link is distinct from the browser's Back button. -->
        <ion-buttons slot="start">
          <ion-button href="../" color="light" aria-label="Handbook homepage">
            <ion-icon slot="start" name="home-outline" aria-hidden="true"></ion-icon>
            Handbook
          </ion-button>
        </ion-buttons>
        <ion-title>
          <span style="display: flex; align-items: center; gap: 16px;">
            <img src="${import.meta.env.BASE_URL}library.svg" alt="" aria-hidden="true"
              style="width: 30px; height: 30px; flex-shrink: 0; filter: brightness(0) invert(1);" />
            <span>The CaRCC AI Facilitation Handbook - Frankenstein</span>
          </span>
        </ion-title>
      </ion-toolbar>
    </ion-header>
    <ion-content scroll-events="true">
      <main class="glossary-page">
        <h1 class="glossary-page-title">Glossary</h1>
        <!-- Keep the instructions and searchbar together in a centred area. -->
        <div class="glossary-search-area">
          <ul class="glossary-instructions">
            <li>Search to find terms. Explore connections between glossary terms.</li>
            <li>Tap an AI lifecycle stage to filter the glossary.</li>
          </ul>
          <ion-searchbar id="glossary-term-search" class="glossary-term-search"
                         placeholder="Search glossary terms" aria-label="Search glossary terms"
                         show-clear-button="always"></ion-searchbar>
        </div>
        <!-- FilteringFlow reads these internal controls; users click the card chips. -->
        <div id="glossary-stage-filters" class="filtering-group" data-group-name="stage" hidden></div>
        <div id="glossary-filter-summary" class="glossary-filter-summary" hidden>
          <span id="glossary-filter-count" aria-live="polite"></span>
          <span id="glossary-selected-stages" class="glossary-filter-selected-stages"
                role="group" aria-label="Selected lifecycle stages"></span>
          <ion-button id="glossary-clear-filters" fill="clear" size="small">Clear filters</ion-button>
        </div>
        <div id="glossary-list" class="glossary-list"></div>
      </main>
      <ion-fab id="glossary-back-to-top" vertical="bottom" horizontal="end" slot="fixed" style="display: none;">
        <ion-fab-button color="primary" size="small" aria-label="Back to top" title="Back to top">
          <ion-icon name="arrow-up-outline" aria-hidden="true"></ion-icon>
        </ion-fab-button>
      </ion-fab>
    </ion-content>
  </ion-app>
`;

const termSearch = document.querySelector("#glossary-term-search");
const list = document.querySelector("#glossary-list");
const stageFilters = document.querySelector("#glossary-stage-filters");
const clearFilters = document.querySelector("#glossary-clear-filters");
const filterSummary = document.querySelector("#glossary-filter-summary");
const filterCount = document.querySelector("#glossary-filter-count");
const selectedStageChips = document.querySelector("#glossary-selected-stages");
const content = document.querySelector("ion-content");
const backToTop = document.querySelector("#glossary-back-to-top");

// Keep the floating Back to Top button out of sight near the start of the page.
content.addEventListener("ionScroll", (event) => {
  backToTop.style.display = event.detail.scrollTop > 450 ? "" : "none";
});
backToTop.addEventListener("click", () => content.scrollToTop(400));

// FilteringFlow uses one internal filter per stage ID, not duplicate filter controls
// on every glossary card. The original Ionic chips are the visible controls.
for (const id of stageIds) {
  const filter = document.createElement("span");
  filter.className = "filtering-filter";
  filter.dataset.filterName = id;
  stageFilters.append(filter);
}

// One column keeps the cards readable without creating uneven desktop rows.
for (const letter of ["0–9", ..."ABCDEFGHIJKLMNOPQRSTUVWXYZ"]) {
  const group = groups.get(letter);
  if (!group) continue;

  const section = document.createElement("section");
  section.id = `letter-${letter}`;
  section.className = "glossary-letter-section";

  const heading = document.createElement("h2");
  heading.textContent = letter;
  heading.className = "glossary-letter-heading";
  section.append(heading);

  const grid = document.createElement("ion-grid");
  grid.setAttribute("fixed", "true");
  grid.className = "glossary-card-grid";

  const row = document.createElement("ion-row");
  grid.append(row);
  section.append(grid);
  list.append(section);

  for (const entry of group) {
    const column = document.createElement("ion-col");
    column.setAttribute("size", "12");
    column.classList.add("filtering-item");
    column.dataset.glossaryTerm = entry.term;
    column.setAttribute("data-filter-stage", entry.stage_ids.join(","));
    row.append(column);
    renderGlossaryCard(column, entry);

    // Match each visible lifecycle chip to its generated filter ID.
    column.querySelectorAll(".glossary-stage-chips ion-chip").forEach((chip, position) => {
      chip.dataset.lifecycleStage = entry.stage_ids[position];
      chip.setAttribute("role", "button");
      chip.setAttribute("tabindex", "0");
      chip.setAttribute("aria-pressed", "false");
      chip.setAttribute("aria-label", `Filter by ${entry.stages[position]}`);
    });
  }
}

// FilterData keeps the existing lifecycle filters (OR across selected stages).
// filtering.js also checks the term prefix, giving AND between search and stages.
const selectedStages = new Set();
let searchQuery = "";
const flow = new FilteringFlow(document.querySelector(".glossary-page"));

// Search canonical term names only, ignoring case. Do not match mid-term words.
flow.filtering.addEventListener("filter-item", ({ data: { item } }) => {
  return item.data.element.dataset.glossaryTerm.toLowerCase().startsWith(searchQuery);
});

flow.addEventListener("filter", ({ data: { result } }) => {
  const active = selectedStages.size > 0 || searchQuery.length > 0;
  filterSummary.hidden = !active;
  selectedStageChips.replaceChildren();
  if (active) {
    filterCount.textContent = `${result.filteredItems.length} of ${entries.length} terms`;
    for (const id of stageIds) {
      if (!selectedStages.has(id)) continue;
      const chip = document.createElement("ion-chip");
      chip.setAttribute("color", "warning");
      chip.setAttribute("outline", "true");
      const label = document.createElement("ion-label");
      label.setAttribute("color", "dark");
      label.textContent = stageNames.get(id);
      chip.append(label);
      selectedStageChips.append(chip);
    }
  }

  // Keep every visible lifecycle chip outlined and dark, with yellow for active stages.
  for (const chip of list.querySelectorAll(".glossary-stage-chips ion-chip")) {
    const checked = selectedStages.has(chip.dataset.lifecycleStage);
    chip.outline = true;
    chip.color = checked ? "warning" : "primary";
    chip.querySelector("ion-label").color = "dark";
    chip.setAttribute("aria-pressed", String(checked));
  }

  // Show a letter heading only when its section contains matching cards.
  for (const section of list.querySelectorAll(".glossary-letter-section")) {
    section.hidden = !section.querySelector("ion-col.filtering-item:not(.filtered)");
  }
});

function applyFilters() {
  const data = new FilterData();
  for (const id of selectedStages) data.checkFilter("stage", id);
  flow.filter(data);
}
applyFilters();

// Remove an old linked-card highlight when starting a different search.
// Change to a nonexistent target first so CSS clears :target, then remove
// the fragment without adding a history entry or changing scroll position.
function clearNavigationHighlight() {
  if (!window.location.hash) return;
  window.location.replace("#glossary-clear-highlight");
  window.history.replaceState(window.history.state, "", window.location.pathname + window.location.search);
}

// Typing or clearing the term search keeps any selected lifecycle stages.
termSearch.addEventListener("ionInput", (event) => {
  searchQuery = (event.detail.value || "").trim().toLowerCase();
  clearNavigationHighlight();
  applyFilters();
});
termSearch.addEventListener("ionClear", () => {
  searchQuery = "";
  clearNavigationHighlight();
  applyFilters();
});

// The lifecycle chips are buttons; Enter and Space work as well as a click.
list.addEventListener("keydown", (event) => {
  if (event.key !== "Enter" && event.key !== " ") return;
  const chip = event.target.closest("ion-chip[data-lifecycle-stage]");
  if (!chip) return;
  event.preventDefault();
  chip.click();
});

// A card chip starts a new stage view when search is active.
// Without search, stage chips toggle so readers can combine stages.
list.addEventListener("click", (event) => {
  const chip = event.target.closest("ion-chip[data-lifecycle-stage]");
  if (!chip) return;
  const id = chip.dataset.lifecycleStage;
  // Remember where this chip was before filtering changes the page layout.
  const chipTop = chip.getBoundingClientRect().top;
  if (searchQuery.length > 0) {
    selectedStages.clear();
    termSearch.value = "";
    searchQuery = "";
  }
  if (selectedStages.has(id)) selectedStages.delete(id);
  else selectedStages.add(id);
  clearNavigationHighlight();
  applyFilters();

  // Keep the clicked chip in place when earlier cards appear or disappear.
  requestAnimationFrame(() => {
    const card = chip.closest("ion-col");
    if (card?.classList.contains("filtered") || card?.closest(".glossary-letter-section")?.hidden) return;
    content.scrollByPoint(0, chip.getBoundingClientRect().top - chipTop, 0);
  });
});

// Clear Filters resets search, lifecycle stages, and the highlighted URL target.
// Keep the current page and scroll position; the searchbar X only clears search.
clearFilters.addEventListener("click", () => {
  selectedStages.clear();
  termSearch.value = "";
  searchQuery = "";
  clearNavigationHighlight();
  applyFilters();
});

// Follow glossary links even when search or lifecycle filters hide their destination.
// Clear the filters before scrolling, so the linked card and its letter heading are visible.
function scrollToHash() {
  const id = window.location.hash.slice(1);
  const target = id ? document.getElementById(id) : null;
  if (!target) return;

  if (selectedStages.size > 0 || searchQuery.length > 0) {
    selectedStages.clear();
    termSearch.value = "";
    searchQuery = "";
    applyFilters();
  }

  target.scrollIntoView({ block: "start" });
}

// A link to the current URL fragment does not fire hashchange again.
// Handle clicks too, so readers can revisit a linked card after filtering.
list.addEventListener("click", (event) => {
  const link = event.target.closest('a[href^="#"]');
  if (link) requestAnimationFrame(scrollToHash);
});

window.addEventListener("hashchange", scrollToHash);
requestAnimationFrame(scrollToHash);
