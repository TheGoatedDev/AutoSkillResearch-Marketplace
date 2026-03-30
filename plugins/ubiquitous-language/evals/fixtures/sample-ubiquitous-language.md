# Ubiquitous Language

## Order Lifecycle

| Term | Context | Definition | Rationale | Aliases to avoid |
| --- | --- | --- | --- | --- |
| **Order** | Sales | A customer's request to purchase one or more items | Chosen over "purchase" — purchase implies completed payment | Purchase, transaction |
| **Invoice** | Billing | A request for payment sent to a customer after delivery | "Bill" is informal and ambiguous with legislative bills | Bill, payment request |

## People

| Term | Context | Definition | Rationale | Aliases to avoid |
| --- | --- | --- | --- | --- |
| **Customer** | Global | A person or organization that places orders | "Client" is ambiguous with API clients | Client, buyer, account |

## Relationships

- An **Order** (Sales) belongs to exactly one **Customer**
- An **Order** (Sales) produces one or more **Invoices** (Billing)

## Example Dialogue

> **Dev:** "When a **Customer** places an **Order**, do we create the **Invoice** immediately?"
> **Domain expert:** "No — an **Invoice** is only generated once fulfillment is confirmed."

## Flagged Ambiguities

- "account" was used to mean both **Customer** and authentication identity — recommend using **Customer** for domain, **User** for auth.

## Deprecated Terms

- `subscription` → use **Membership** — subscriptions imply recurring billing, ours are fixed-term
