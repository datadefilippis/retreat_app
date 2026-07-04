/**
 * MarkdownLite — tiny, safe markdown renderer (zero dependencies).
 *
 * Extracted from EventLandingPage.js (F4 Onda 11) so the Terms &
 * Conditions block at checkout can reuse the same renderer without
 * introducing a new library.
 *
 * Syntax supported:
 *   # / ## / ### headings
 *   **bold**
 *   *italic*
 *   - list-item  (also: * list-item)
 *   blank lines split paragraphs
 *
 * Everything else is HTML-escaped, so untrusted input is rendered
 * safely — the caller can feed it values coming straight from the
 * public API.
 *
 * Usage:
 *   <MarkdownLite source={product.terms_content} />
 */

import React from 'react';


function escapeHTML(s) {
  return (s || '')
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;')
    .replace(/'/g, '&#39;');
}


function renderInline(text) {
  const escaped = escapeHTML(text);
  return escaped
    .replace(/\*\*(.+?)\*\*/g, '<strong>$1</strong>')
    .replace(/(^|[^\*])\*(?!\s)([^\*]+?)\*/g, '$1<em>$2</em>');
}


export default function MarkdownLite({ source }) {
  if (!source) return null;
  const lines = String(source).split('\n');
  const blocks = [];
  let paragraph = [];
  let listItems = [];

  const flushParagraph = () => {
    if (paragraph.length) {
      blocks.push({ type: 'p', html: renderInline(paragraph.join(' ')) });
      paragraph = [];
    }
  };
  const flushList = () => {
    if (listItems.length) {
      blocks.push({ type: 'ul', items: listItems.map(renderInline) });
      listItems = [];
    }
  };

  for (const raw of lines) {
    const line = raw.trim();
    if (!line) {
      flushParagraph();
      flushList();
      continue;
    }
    if (line.startsWith('### ')) {
      flushParagraph(); flushList();
      blocks.push({ type: 'h3', html: renderInline(line.slice(4)) });
    } else if (line.startsWith('## ')) {
      flushParagraph(); flushList();
      blocks.push({ type: 'h2', html: renderInline(line.slice(3)) });
    } else if (line.startsWith('# ')) {
      flushParagraph(); flushList();
      blocks.push({ type: 'h1', html: renderInline(line.slice(2)) });
    } else if (line.startsWith('- ') || line.startsWith('* ')) {
      flushParagraph();
      listItems.push(line.slice(2));
    } else {
      flushList();
      paragraph.push(line);
    }
  }
  flushParagraph();
  flushList();

  return (
    <div className="prose prose-sm max-w-none text-gray-700 space-y-3">
      {blocks.map((b, i) => {
        if (b.type === 'h1') return <h1 key={i} className="text-2xl font-bold text-gray-900" dangerouslySetInnerHTML={{ __html: b.html }} />;
        if (b.type === 'h2') return <h2 key={i} className="text-xl font-semibold text-gray-900 mt-4" dangerouslySetInnerHTML={{ __html: b.html }} />;
        if (b.type === 'h3') return <h3 key={i} className="text-base font-semibold text-gray-900 mt-3" dangerouslySetInnerHTML={{ __html: b.html }} />;
        if (b.type === 'p') return <p key={i} className="leading-relaxed" dangerouslySetInnerHTML={{ __html: b.html }} />;
        if (b.type === 'ul') return (
          <ul key={i} className="list-disc list-inside space-y-1">
            {b.items.map((it, j) => <li key={j} dangerouslySetInnerHTML={{ __html: it }} />)}
          </ul>
        );
        return null;
      })}
    </div>
  );
}
