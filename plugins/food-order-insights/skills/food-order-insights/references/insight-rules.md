# Insight rules

Read this reference when producing inferred patterns, calorie estimates, period labels, or meal suggestions.

## Evidence levels

Keep three classes visibly separate:

- **Receipt fact:** directly present in the email, such as item name, price, restaurant, or time.
- **Estimate:** derived from typical servings, such as calories or broad nutritional characteristics.
- **User-confirmed context:** a label supplied by the user, such as busy, ill, or travelling.

Never present an estimate or inferred context as a receipt fact.

## Calories

- Estimate a low-to-high range per item using the named dish, quantity, size, extras, and cooking method when visible.
- Widen the range when portion size, ingredients, or preparation are unknown.
- Use confidence `high` only when the receipt provides portion or nutrition information, `medium` for a well-known dish with clear size, and `low` otherwise.
- Aggregate low bounds and high bounds separately.
- State the percentage of orders or items with low-confidence estimates.
- Do not infer weight change, energy requirements, deficiencies, or disease risk from food-order emails.

## Food-pattern observations

Use neutral, descriptive language. Suitable observations include frequency of fried dishes, estimated vegetable variety, repeated sweetened drinks, late ordering, or reliance on a narrow set of meals. Do not label foods or users as good, bad, clean, unhealthy, disciplined, or failing.

Avoid condition-specific advice. If a user asks about diabetes, pregnancy, allergies, an eating disorder, medication, or another diagnosed condition, explain that receipt-based estimates are insufficient and recommend appropriate professional guidance.

## Delivery-heavy periods

Compare a week with the user's own recent baseline, not a universal threshold. Flag a candidate period when at least two signals are meaningfully elevated:

- order count;
- total delivery spend;
- consecutive ordering days;
- late-hour orders;
- unusually low meal variety.

Describe the evidence, then ask the user for context. Allowed suggested labels are `busy`, `ill`, `travel`, `social`, `no kitchen`, and `other`. Never infer illness as fact.

## Meal suggestions

Base suggestions on observed orders and preserve what likely makes the meal appealing: cuisine, format, texture, sauce, convenience, or comfort. Prefer recurring meals when enough history exists. With fewer than three relevant occurrences, suggestions are still allowed but must be labelled as based on limited evidence rather than a stable pattern. Prefer familiar substitutions over unrelated idealized meals.

Rank suggestions by:

1. frequency of the source order;
2. ease and prep time;
3. likely improvement in vegetable, fiber, protein, or cooking-method balance;
4. ingredient overlap across several suggestions;
5. prior accept/dislike feedback.

For each suggestion, provide why it matches, approximate prep time, a short ingredient list, and no more than five steps. Offer at most five at once.

If the user dislikes a suggestion, use the reason only to improve later suggestions. Do not interpret food preferences as health or personality traits.

## Lifestyle changes

Translate no more than three findings into active experiments. Prefer changes that preserve cuisine, convenience, price range, and comfort instead of replacing the user's routine wholesale.

Every recommendation must show:

- the receipt pattern behind it;
- the smallest useful action;
- why it may help in ordinary, non-clinical language;
- effort and approximate preparation time;
- a one- or two-week progress measure;
- an easier fallback.

Use the user's own prior period as the comparison baseline. Treat an accepted or disliked recommendation as preference feedback, not evidence about health, motivation, or character. If no durable host memory exists, say that the feedback applies only to the current conversation or project context.
