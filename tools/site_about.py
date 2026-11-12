"""The "How this guide works" page (about/index.html): a walk-through for CDC, reviewers, and readers."""

from __future__ import annotations

import html


def esc(text) -> str:
    return html.escape(str(text), quote=True)


def page(root: str, guide: dict, stats: dict, by_id: dict) -> str:
    def card(cid: str, label: str | None = None, anchor: str = "") -> str:
        c = by_id.get(cid)
        if not c:
            return esc(label or cid)
        return f'<a href="{root}{c.id}/index.html{anchor}">{esc(label or (c.number + " " + c.title))}</a>'

    s = stats
    return f"""<article class="page about">
<p class="eyebrow">About this draft</p>
<h1>How this guide works</h1>
<p class="lede">This website is a working draft of the {esc(guide['title'])}, {esc(guide['release'])}, a joint publication of
CDC and AIRA. It presents the same content as the Word draft and the IGAMT conformance profiles. The content is split into short
sections that link to each other, and quality checks run on every change. This page walks through what the site does and how
it is built.</p>

<nav class="page-toc" aria-label="On this page"><ol>
<li><a href="#finding">Finding your way</a></li>
<li><a href="#section">Reading a section</a></li>
<li><a href="#structure">Message structure (chapter 7)</a></li>
<li><a href="#examples">Example messages (appendix A)</a></li>
<li><a href="#comments">Commenting</a></li>
<li><a href="#quality">Quality review</a></li>
<li><a href="#built">How it is built, and what is authoritative</a></li>
<li><a href="#next">What comes next</a></li>
</ol></nav>

<section id="finding"><h2>Finding your way</h2>
<ul>
<li><strong>The contents</strong> on the left show the whole guide as a tree: chapters 1–6 (the narrative), chapter 7 (message
structure, generated from IGAMT), and appendices A–C. It opens to where you are. On a phone, it is behind the ☰ button.</li>
<li><strong>The filter</strong> at the top of the contents narrows the tree to the sections that match. It is not a full-text
search. It matches section titles and each section's <em>filter terms</em>:
<ul>
<li>the fields, codes, profiles, and value sets the section mentions, found automatically;</li>
<li>a curated list of topics (still a first draft), such as <em>refusal</em>, <em>VFC</em>, <em>consent</em>, or <em>forecast</em>.</li>
</ul>
Try <code>RXA-20</code>, <code>RXA-20 RE</code> (every word must match), <code>PD1-12</code>, <code>refusal</code>, or <code>RXA</code>
(all RXA fields). <code>RXA-2</code> finds RXA-2 and never RXA-20. The terms that matched show under each result, and the filter
stays on while you move between pages.</li>
<li><strong>Links everywhere.</strong> Field references in the text (such as RXA-11), profile codes (Z22), and value set IDs link
to their pages in chapter 7. Hover over one to see the field's name.</li>
<li><strong>Permanent links.</strong> Every section has a permanent address, and <em>Copy link</em> copies it. Each conformance
statement has its own link too: select its number (<code>s1</code>, <code>s2</code>, …). Addresses are based on IDs that do
not change when sections are renumbered or retitled, so links in email, minutes, and comments keep working.</li>
</ul>
</section>

<section id="section"><h2>Reading a section</h2>
<p>Each section ({card('unnamed-newborns', 'for example, Unnamed Newborns')}) is one focused topic. It has these parts, in order:</p>
<ol>
<li><strong>Narrative:</strong> the explanation, in a few paragraphs.</li>
<li><strong>Conformance statements:</strong> the requirements, one per line, each with its verb (SHALL, SHOULD, MAY, …) as a
colored label and its own number and link.</li>
<li><strong>Examples:</strong> complete example messages that illustrate the section (see below).</li>
<li><strong>Message structure for the fields on this page:</strong> a collapsible table showing, for every field the section
mentions, its usage and cardinality in each message profile, the value sets that govern its codes, and the conformance statements
that test it. You don't have to leave the page to check what the profiles say.</li>
<li><strong>Figures, resources cited, and the sub-sections</strong>, then the section's filter terms. Selecting a term filters
the contents by it.</li>
</ol>
<p>{s['cards']} sections hold {s['statements']} conformance statements. Many requirements were written as plain paragraphs in the
Word draft. They are shown as numbered statements here, with their wording unchanged, and each section where this was done says
so in its quality notes.</p>
</section>

<section id="structure"><h2>Message structure (chapter 7)</h2>
<p><a href="{root}structure/index.html">Chapter 7</a> is generated from the IGAMT conformance export:</p>
<ul>
<li><strong>Message profiles</strong> ({s['profiles']}): each profile's segment tree, with usage and cardinality, the slices
(for example, the RXA flavors Z22 uses for administered, historical, refused, and other doses), and its conformance statements.
See <a href="{root}structure/profiles/z22/index.html">Z22</a>.</li>
<li><strong>Segments:</strong> one page per segment comparing every field across all its flavors, so differences stand out. It
also lists the narrative sections that discuss each field. See <a href="{root}structure/segments/rxa/index.html">RXA</a>.</li>
<li><strong>Segment flavors, data types, and value sets</strong> ({s['value_sets']} value sets, with their codes and where
each is bound).</li>
<li><strong>OBX co-constraint tables:</strong> which observations belong in each kind of order group. See
<a href="{root}structure/coconstraints/z22/index.html">Z22 co-constraints</a>.</li>
</ul>
</section>

<section id="examples"><h2>Example messages (appendix A)</h2>
<p><a href="{root}examples/index.html">{s['examples']} examples</a> from CDC's example list appear on the sections they illustrate.
See {card('required-data-elements', 'Refusal: Required Data Elements')}.</p>
<ul>
<li><strong>Complete messages.</strong> Many examples were drafted as clips: only the segment that matters. The site completes
each clip from a base message, so every example is a whole message you can copy and test.</li>
<li><strong>Highlighting.</strong> The segments an example is about are highlighted, and the fields that differ from the base
message are marked. Hover over any field to see its position and name.</li>
<li><strong>Checked on every build.</strong> Each example is checked against the IGAMT profiles: segments, required and
unsupported fields, codes, date/time formats, conformance statements, and co-constraints. The results are shown under each message.
{s['examples_clean']} of {s['examples']} currently have no problems of their own.</li>
</ul>
</section>

<section id="comments"><h2>Commenting</h2>
<p>Every page ends with a <strong>Comments</strong> panel. Comments are stored in InteropHub, on the
<a href="{esc(guide.get('interophub_topic', '#'))}">CDC HL7 v2 Guide (Release 2)</a> topic. Sign in with your InteropHub account
to read and add comments. One sign-in covers the whole site.</p>
<ul>
<li>A comment belongs to the section. Use <em>About</em> to say whether it concerns the whole section, a specific conformance
statement, a figure, or an example.</li>
<li>Reply to a comment to discuss it. Edit or withdraw your own comments.</li>
<li>Editors of the topic can record a <strong>disposition</strong> (Persuasive, Not Persuasive, …) with a change note, and
close the thread. The same comments are available in InteropHub, and links from InteropHub open the right section.</li>
<li>Sections with comments show a 💬 count in the contents; blue means some are still open.</li>
</ul>
</section>

<section id="quality"><h2>Quality review</h2>
<p>Automated checks and an editorial review run on every change. Their results, called <strong>findings</strong>, appear in a
panel at the top of the section they concern, and in the <a href="{root}quality/index.html">Quality review</a> list
({s['findings']} findings now). They are for the authors and reviewers. They are not part of the guide, and
<strong>Hide findings</strong> (top right) turns them off for reading.</p>
<ul>
<li><strong>Severity:</strong> <em>issue</em> (likely wrong), <em>warning</em> (inconsistent or unclear), <em>note</em> (worth
considering).</li>
<li><strong>What is checked:</strong> structure and length of sections, conformance language (verbs in narrative, statements
without a responsible party, compound requirements), figures, references and glossary pointers, the example messages, and the
narrative against the IGAMT profiles.</li>
<li><strong><a href="{root}quality/igamt/index.html">Narrative vs IGAMT</a></strong> compares what the text says about fields,
codes, and observations with the conformance profiles. It answers the review comments in the Word draft that asked for this
check, and it lists change requests for IGAMT. Each of its findings needs CDC's verification before anything is changed.</li>
<li>Every finding has a permanent ID. All findings can be downloaded as a spreadsheet:
<a href="{root}quality/findings.csv">findings.csv</a>.</li>
</ul>
</section>

<section id="built"><h2>How it is built, and what is authoritative</h2>
<p>Nothing on this site is copied by hand. A build runs on every change and regenerates every page from three sources:</p>
<div class="table-wrap"><table><thead><tr><th>Content</th><th>Source today</th><th>How it gets here</th></tr></thead><tbody>
<tr><td>Narrative (chapters 1–6), glossary, resources</td><td>CDC's Word draft</td><td>Converted into the section tree. Section and
statement IDs stay the same from one draft to the next.</td></tr>
<tr><td>Message structure (chapter 7)</td><td>IGAMT, the authoritative source for structure</td><td>Read from the IGAMT export. Corrections
are made in IGAMT and appear here with the next export. Nothing in chapter 7 is edited by hand.</td></tr>
<tr><td>Example messages (appendix A)</td><td>CDC's example list and the drafted samples</td><td>Imported, completed into whole messages,
and checked against the profiles.</td></tr>
</tbody></table></div>
<p>The converted content and the tools are public on <a href="{esc(guide['repository'])}">GitHub</a>. The Word draft, the IGAMT
export, and the example files themselves are not published. The footer of each page shows which draft and which build it
comes from.</p>
</section>

<section id="next"><h2>What comes next</h2>
<ul>
<li><strong>Editing here instead of in Word.</strong> Today the narrative is converted from Word each time. Once CDC is ready,
the section tree can become the place the narrative is edited. Changes would then be made section by section, with every edit
tracked and checked automatically, and the Word conversion would be retired. IGAMT would remain the source for the message
structure.</li>
<li><strong>Ballot document.</strong> For the HL7 ballot, a Word/PDF document holding the complete content would be generated
from the same sources, and this site offered as an alternative way to read it.</li>
<li><strong>Branding.</strong> Colors and logos are provisional until confirmed by CDC.</li>
</ul>
<p>Questions or ideas about the site itself are welcome as comments on this page.</p>
</section>
</article>"""
