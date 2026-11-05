// Render a CaRCC Glossary Explorer card using Ionic components.
import { defineCustomElement as defineIonCard } from "@ionic/core/components/ion-card.js";
import { defineCustomElement as defineIonCardHeader } from "@ionic/core/components/ion-card-header.js";
import { defineCustomElement as defineIonCardTitle } from "@ionic/core/components/ion-card-title.js";
import { defineCustomElement as defineIonCardContent } from "@ionic/core/components/ion-card-content.js";
import { defineCustomElement as defineIonChip } from "@ionic/core/components/ion-chip.js";
import { defineCustomElement as defineIonLabel } from "@ionic/core/components/ion-label.js";
import MarkdownIt from "markdown-it";

const markdown = new MarkdownIt();
const escapeHtml = (value) => markdown.utils.escapeHtml(String(value));

// Match MkDocs glossary heading anchors, including terms with punctuation.
// The Python linking hook uses Markdown's ASCII slugify convention.
function slugify(term) {
  return term.normalize("NFKD")
    .replace(/[^\x00-\x7F]/g, "")
    .replace(/[^\w\s-]/g, "")
    .trim()
    .toLowerCase()
    .replace(/[-\s]+/g, "-");
}

export function registerGlossaryCardComponents() {
  defineIonCard();
  defineIonCardHeader();
  defineIonCardTitle();
  defineIonCardContent();
  defineIonChip();
  defineIonLabel();
}

export function renderGlossaryCard(container, entry) {
  // All lifecycle chips use Ionic primary outlines; their text stays dark.
  const stages = (entry.stages || []).map((stage) => `
    <ion-chip outline="true" color="primary">
      <ion-label color="dark">${escapeHtml(stage)}</ion-label>
    </ion-chip>
  `).join("");

  const relationships = new Map();
  for (const relationship of entry.relationships || []) {
    const label = relationship.label;
    if (!relationships.has(label)) relationships.set(label, []);
    relationships.get(label).push(relationship.term);
  }

  // A slash separates the singular and plural labels provided by the spreadsheet.
  // Count each label group independently; labels without a slash stay unchanged.
  const relationshipRows = Array.from(relationships, ([label, terms]) => {
    const forms = label.split(/\s*\/\s*/);
    const heading = forms.length === 2 ? forms[terms.length === 1 ? 0 : 1] : label;

    return `
      <div class="glossary-relationship-row">
        <span class="glossary-relationship-label">${escapeHtml(heading)}:</span>
        <span class="glossary-chip-list glossary-relationship-chips">
          ${terms.map((term) => `
            <ion-chip outline="true">
              <ion-label color="dark">
                <a href="#${slugify(term)}">${escapeHtml(term)}</a>
              </ion-label>
            </ion-chip>
          `).join("")}
        </span>
      </div>
    `;
  }).join("");

  container.innerHTML = `
    <div class="glossary-card-layout">
      <ion-card id="${slugify(entry.term)}">
        <ion-card-header>
          <ion-card-title color="primary"><strong>${escapeHtml(entry.term)}</strong></ion-card-title>
        </ion-card-header>
        <ion-card-content>
          <div class="glossary-definition">${markdown.render(entry.definition)}</div>
          ${stages ? `
            <section class="glossary-card-section" aria-label="AI lifecycle stages">
              <h3 class="glossary-section-heading">AI LIFECYCLE STAGES</h3>
              <div class="glossary-chip-list glossary-stage-chips">${stages}</div>
            </section>
          ` : ""}
          ${relationshipRows ? `
            <section class="glossary-card-section" aria-label="Connected terms">
              <h3 class="glossary-section-heading">CONNECTED TERMS</h3>
              ${relationshipRows}
            </section>
          ` : ""}
        </ion-card-content>
      </ion-card>
    </div>
  `;
}
