---
title: Guide | Filipino Talent
description: Step-by-step guide to put your portfolio on a free filipino-talent.com subdomain.
---

# Guide

Written for people who can fill out forms and copy-paste. You do not need to know
what DNS means. You only need a site that is already online.

## Before you start

- A portfolio that is **already published**, with a link you can open in a browser (for example `https://juan-dela-cruz.github.io`).
- A **Google account** to sign in with.
- An idea of the **subdomain** you want, usually your name.

> **Which hosts work?** GitHub Pages, Cloudflare Pages, Vercel, and Netlify —
> all free with a plain CNAME. Builders like Wix, Canva, and WordPress.com need
> a paid plan and their own DNS records, so they are not supported here. See
> [Using Canva](/guide/canva) for free alternatives.

## 1. Pick the host you already use

If your site is already online, skip to step 2. Otherwise choose one and follow
its guide:

| Host | Free? | Guide |
| --- | --- | --- |
| GitHub Pages | Yes | [GitHub Pages](/guide/github-pages) |
| Cloudflare Pages | Yes | [Cloudflare Pages](/guide/cloudflare-pages) |
| Netlify | Yes | [Netlify](/guide/netlify) |
| Vercel | Yes | [Vercel](/guide/vercel) |
| Canva | No (custom domain) | [Canva workarounds](/guide/canva) |

## 2. Your host's target

Your subdomain points at your host's address. Most of the time this is simply
the address you already gave as your portfolio URL, with the `https://` and
anything after the first `/` removed. The form fills it in for you, so you can
skip this step unless your host gives you a different target.

| Host | What you enter as the target |
| --- | --- |
| GitHub Pages | `yourusername.github.io` |
| Cloudflare Pages | `your-project.pages.dev` |
| Netlify | `your-site.netlify.app` |
| Vercel | `your-project.vercel.app` |

If you do need to change it, edit the target field in the form and enter it as a
[CNAME](/guide#what-is-a-cname), with no `https://` and no path.

## 3. Submit the form

Go to [Get a subdomain](/submit) and sign in with Google. Then fill in:

- the subdomain you want,
- your full legal name (used only for review),
- your portfolio URL,
- your GitHub username (optional),
- the record type (**CNAME** for most people),
- the target (filled in automatically; only change it under **Advanced** if your
  host told you a specific target).

Your Google email is private and is never published.

## 4. It goes live

Your subdomain is published immediately after you submit. Google confirms that
the account is yours, so there is no confirmation email to send. A maintainer
also reviews published subdomains and may remove any that break the rules.

## 5. Connect it at your host

DNS alone is not enough — your host also has to agree to answer for the
subdomain.

1. Go to [Connect your subdomain](/guide/connect) and follow the steps for
   GitHub Pages, Cloudflare Pages, Vercel, or Netlify.
2. Wait a few minutes for HTTPS. The first certificate can take up to an hour.
3. Open `https://yourname.filipino-talent.com` and confirm it loads.

If something does not work, see [Troubleshooting](/guide/troubleshooting).

---

## What is a CNAME?

A CNAME is a DNS record that says "this name is an alias for that other name."
When you point `yourname.filipino-talent.com` at `yourusername.github.io`, you
are telling the internet to load your GitHub Pages site at your new address.

It is the easiest option because when your host changes servers, things keep
working automatically.

## Do I keep it forever?

No. This is for aspiring remote workers. Once you can afford your own domain,
release your subdomain from your [account](/account) (or email
`remove@filipino-talent.com` if you cannot sign in) to free the name for the next
person.

## What about email?

This service only handles the website address (DNS records for the web). It does
**not** provide email mailboxes at your subdomain.
