/*
 * Prevent glossary tooltips from staying open after Back/Forward navigation.
 *
 * Windows browsers send mouseleave during navigation, telling Material
 * the pointer has left. In macOS Safari, that event appears to be missed,
 * leaving the tooltip open when the cached page is restored.
 *
 * This script sends mouseleave when a cached page is restored, allowing
 * Material to clear its hover state and close the glossary tooltip.
 */

window.addEventListener("pageshow", (event) => {
  if (!event.persisted) return;

  document.querySelectorAll("a.glossary-link abbr").forEach((term) => {
    const tooltipId = term.getAttribute("aria-describedby");
    const tooltip = tooltipId
      ? document.getElementById(tooltipId)
      : null;

    // Let Material clear its own hover state and remove the tooltip.
    tooltip?.dispatchEvent(new MouseEvent("mouseleave"));
    term.dispatchEvent(new MouseEvent("mouseleave"));
  });
});