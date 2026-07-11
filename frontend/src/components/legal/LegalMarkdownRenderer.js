import React from 'react';

/**
 * LegalMarkdownRenderer — Wave GDPR-Admin Phase C (2026-05-16).
 *
 * Renders a small, predictable subset of GitHub-flavoured Markdown
 * used by the AFianco legal documents (Privacy Policy + Terms of
 * Service). Pure component, no external dependencies.
 *
 * Supported syntax:
 *   - # / ## / ### headings → h1 / h2 / h3
 *   - **bold** → <strong>
 *   - *italic* → <em>
 *   - `code` → <code> (inline)
 *   - > blockquote (single-line, used for the "translation in progress"
 *     banner at the top of EN/DE/FR drafts)
 *   - Unordered lists (lines starting with "- " or "* ")
 *   - GFM tables (| col | col | with separator |---|---|)
 *   - Plain paragraphs (other text)
 *   - mailto: links (auto-detected for foo@bar)
 *
 * NOT supported: ordered lists, images, footnotes, nested lists, HTML,
 * raw <script> (intentionally — these legal docs use a stable subset).
 *
 * The renderer reuses the Tailwind classes from the original JSX
 * PrivacyPolicyPage.js so the visual rendering matches the pre-Phase-C
 * version pixel-for-pixel.
 */
const LegalMarkdownRenderer = ({ content }) => {
  if (!content || typeof content !== 'string') return null;

  const blocks = parseBlocks(content);

  return (
    <div className="prose prose-sm max-w-none space-y-6 text-foreground">
      {blocks.map((block, idx) => renderBlock(block, idx))}
    </div>
  );
};

/* ── Block-level parser ──────────────────────────────────────────────── */

function parseBlocks(text) {
  const lines = text.split('\n');
  const blocks = [];
  let i = 0;

  while (i < lines.length) {
    const line = lines[i];

    // Skip blank lines between blocks
    if (line.trim() === '') {
      i += 1;
      continue;
    }

    // Heading 1 / 2 / 3
    const headingMatch = line.match(/^(#{1,3})\s+(.+)$/);
    if (headingMatch) {
      blocks.push({
        type: 'heading',
        level: headingMatch[1].length,
        text: headingMatch[2],
      });
      i += 1;
      continue;
    }

    // Blockquote (single or multi-line — used for the translation banner)
    if (line.startsWith('> ')) {
      const quoteLines = [];
      while (i < lines.length && lines[i].startsWith('> ')) {
        quoteLines.push(lines[i].slice(2));
        i += 1;
      }
      blocks.push({ type: 'blockquote', text: quoteLines.join(' ') });
      continue;
    }

    // Table: line starts with "| " and the next line is the header separator
    if (line.startsWith('|') && i + 1 < lines.length && /^\|\s*[-:]+\s*\|/.test(lines[i + 1])) {
      const headerCells = parseTableRow(line);
      // skip the separator
      i += 2;
      const rows = [];
      while (i < lines.length && lines[i].startsWith('|')) {
        rows.push(parseTableRow(lines[i]));
        i += 1;
      }
      blocks.push({ type: 'table', header: headerCells, rows });
      continue;
    }

    // Ordered list (lines starting with "1. " / "2) " ...) — SEO1b:
    // gli articoli del magazine usano elenchi numerati (criteri,
    // protocolli passo-passo) che finivano fusi in un paragrafo unico
    if (/^\d+[.)]\s+/.test(line)) {
      const items = [];
      while (i < lines.length && /^\d+[.)]\s+/.test(lines[i])) {
        items.push(lines[i].replace(/^\d+[.)]\s+/, ''));
        i += 1;
      }
      blocks.push({ type: 'olist', items });
      continue;
    }

    // Unordered list (lines starting with "- " or "* ")
    if (/^[-*]\s+/.test(line)) {
      const items = [];
      while (i < lines.length && /^[-*]\s+/.test(lines[i])) {
        items.push(lines[i].replace(/^[-*]\s+/, ''));
        i += 1;
      }
      blocks.push({ type: 'list', items });
      continue;
    }

    // Plain paragraph — gather consecutive non-empty, non-special lines
    const paraLines = [];
    while (
      i < lines.length &&
      lines[i].trim() !== '' &&
      !lines[i].match(/^(#{1,3})\s+/) &&
      !lines[i].startsWith('> ') &&
      !lines[i].startsWith('|') &&
      !/^[-*]\s+/.test(lines[i]) &&
      !/^\d+[.)]\s+/.test(lines[i])
    ) {
      paraLines.push(lines[i]);
      i += 1;
    }
    if (paraLines.length > 0) {
      blocks.push({ type: 'paragraph', text: paraLines.join(' ') });
    }
  }

  return blocks;
}

function parseTableRow(line) {
  // Strip leading/trailing pipes, split on |, trim cells
  return line
    .replace(/^\||\|$/g, '')
    .split('|')
    .map((c) => c.trim());
}

/* ── Inline renderer (bold / italic / code / mailto) ─────────────────── */

function renderInline(text, keyPrefix = 'inline') {
  // Split on **bold**, *italic*, `code`, and email-like patterns.
  // Order matters: bold (greedy) before italic to avoid conflict.
  const parts = [];
  let remaining = text;
  let idx = 0;

  // Regex for: **bold** | `code` | *italic* | email | plain
  // SEO1 — link markdown [testo](url): solo percorsi interni, https e
  // mailto (whitelist: il contenuto merchant resta sanitizzato a monte).
  const tokenRe = /(\[[^\]]+\]\((?:\/|https?:\/\/|mailto:)[^)\s]+\))|(\*\*[^*]+\*\*)|(`[^`]+`)|(\*[^*]+\*)|([A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,})/g;
  let match;
  let last = 0;

  while ((match = tokenRe.exec(remaining)) !== null) {
    // Plain text before the match
    if (match.index > last) {
      parts.push(remaining.slice(last, match.index));
    }
    const tok = match[0];
    const linkMatch = tok.match(/^\[([^\]]+)\]\(([^)]+)\)$/);
    if (linkMatch) {
      const [, label, href] = linkMatch;
      const external = href.startsWith('http');
      parts.push(
        <a
          key={`${keyPrefix}-l-${idx++}`}
          href={href}
          className="text-primary underline underline-offset-2"
          {...(external ? { target: '_blank', rel: 'noopener noreferrer' } : {})}
        >
          {label}
        </a>
      );
    } else if (tok.startsWith('**') && tok.endsWith('**')) {
      parts.push(
        <strong key={`${keyPrefix}-b-${idx++}`}>{tok.slice(2, -2)}</strong>
      );
    } else if (tok.startsWith('`') && tok.endsWith('`')) {
      parts.push(
        <code
          key={`${keyPrefix}-c-${idx++}`}
          className="rounded bg-muted px-1 py-0.5 text-xs font-mono"
        >
          {tok.slice(1, -1)}
        </code>
      );
    } else if (tok.startsWith('*') && tok.endsWith('*')) {
      parts.push(<em key={`${keyPrefix}-i-${idx++}`}>{tok.slice(1, -1)}</em>);
    } else if (tok.includes('@')) {
      parts.push(
        <a
          key={`${keyPrefix}-m-${idx++}`}
          href={`mailto:${tok}`}
          className="text-primary underline"
        >
          {tok}
        </a>
      );
    }
    last = match.index + tok.length;
  }
  if (last < remaining.length) {
    parts.push(remaining.slice(last));
  }
  return parts.length === 0 ? remaining : parts;
}

/* ── Block-level renderer ─────────────────────────────────────────────── */

function renderBlock(block, idx) {
  const key = `b-${idx}`;
  switch (block.type) {
    case 'heading': {
      const Tag = `h${block.level}`;
      const className =
        block.level === 1
          ? 'font-heading text-3xl font-bold mb-2'
          : block.level === 2
          ? 'text-xl font-semibold mt-8 mb-3'
          : 'text-lg font-medium mt-6 mb-2';
      return React.createElement(
        Tag,
        { key, className },
        renderInline(block.text, key)
      );
    }
    case 'paragraph':
      return (
        <p key={key} className="text-muted-foreground leading-relaxed">
          {renderInline(block.text, key)}
        </p>
      );
    case 'olist':
      return (
        <ol
          key={key}
          className="list-decimal list-inside text-muted-foreground space-y-2 ml-2"
        >
          {block.items.map((item, i) => (
            <li key={`${key}-${i}`}>{renderInline(item, `${key}-${i}`)}</li>
          ))}
        </ol>
      );
    case 'list':
      return (
        <ul
          key={key}
          className="list-disc list-inside text-muted-foreground space-y-1 ml-2"
        >
          {block.items.map((item, i) => (
            <li key={`${key}-${i}`}>{renderInline(item, `${key}-${i}`)}</li>
          ))}
        </ul>
      );
    case 'blockquote':
      return (
        <blockquote
          key={key}
          className="border-l-4 border-warning bg-warning/10 p-4 text-sm text-foreground"
        >
          {renderInline(block.text, key)}
        </blockquote>
      );
    case 'table':
      return (
        <div key={key} className="overflow-x-auto">
          <table className="w-full text-sm text-muted-foreground border border-border rounded-md">
            <thead>
              <tr className="bg-muted/50">
                {block.header.map((h, i) => (
                  <th
                    key={`${key}-h-${i}`}
                    className="text-left p-3 font-medium"
                  >
                    {renderInline(h, `${key}-h-${i}`)}
                  </th>
                ))}
              </tr>
            </thead>
            <tbody>
              {block.rows.map((row, ri) => (
                <tr key={`${key}-r-${ri}`} className="border-t border-border">
                  {row.map((cell, ci) => (
                    <td key={`${key}-r-${ri}-c-${ci}`} className="p-3">
                      {renderInline(cell, `${key}-r-${ri}-c-${ci}`)}
                    </td>
                  ))}
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      );
    default:
      return null;
  }
}

export default LegalMarkdownRenderer;
