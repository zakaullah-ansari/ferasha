import { BadgeCheck } from "lucide-react";

import type { Review, ReviewSummary } from "@/lib/api/types";
import { formatDate } from "@/lib/format";
import { coverageAsDescribed, FIT_LABELS, usualFit } from "@/lib/reviews";

import { ReviewForm } from "./ReviewForm";
import { Stars } from "./Stars";

function Summary({ summary }: { summary: ReviewSummary }) {
  const fit = usualFit(summary);
  const coverage = coverageAsDescribed(summary);
  return (
    <div className="grid gap-6 sm:grid-cols-[auto_1fr] sm:gap-10">
      <div>
        <p className="font-display text-5xl leading-none">{summary.average}</p>
        <Stars rating={Number(summary.average)} className="mt-2" />
        <p className="mt-1 text-sm text-muted-foreground">
          {summary.count} {summary.count === 1 ? "review" : "reviews"}
        </p>
      </div>
      <div className="grid gap-4">
        <dl className="grid gap-1.5">
          {(["5", "4", "3", "2", "1"] as const).map((stars) => (
            <div key={stars} className="grid grid-cols-[3.75rem_1fr_2rem] items-center gap-3 text-sm">
              <dt className="text-muted-foreground">{stars} {stars === "1" ? "star" : "stars"}</dt>
              <dd aria-hidden="true" className="h-1.5 overflow-hidden rounded-full bg-muted">
                <span className="block h-full rounded-full bg-gold-500" style={{ width: `${(summary.distribution[stars] / summary.count) * 100}%` }} />
              </dd>
              <dd className="text-right tabular-nums">{summary.distribution[stars]}</dd>
            </div>
          ))}
        </dl>
        <ul className="flex flex-wrap gap-x-6 gap-y-1 text-sm">
          {fit && (
            <li>
              Fit: <span className="font-medium">most say {FIT_LABELS[fit].toLowerCase()}</span>
            </li>
          )}
          {coverage !== null && (
            <li>
              Coverage as described: <span className="font-medium">{coverage}% say yes</span>
            </li>
          )}
        </ul>
      </div>
    </div>
  );
}

function ReviewCard({ review }: { review: Review }) {
  return (
    <article className="grid gap-2 border-t py-6">
      <div className="flex flex-wrap items-center gap-x-3 gap-y-1">
        <Stars rating={review.rating} />
        {review.title && <h3 className="font-medium">{review.title}</h3>}
      </div>
      {review.body && <p className="max-w-prose leading-relaxed text-muted-foreground">{review.body}</p>}
      <p className="flex flex-wrap items-center gap-x-3 gap-y-1 text-xs text-muted-foreground">
        <span className="text-foreground">{review.author_name}</span>
        {review.is_verified_purchase && (
          <span className="inline-flex items-center gap-1 text-primary">
            <BadgeCheck aria-hidden="true" className="size-3.5" />
            Verified purchase
          </span>
        )}
        {review.fit_feedback && <span>Fit: {FIT_LABELS[review.fit_feedback]}</span>}
        {review.modesty_as_described !== null && (
          <span>{review.modesty_as_described ? "Coverage as described" : "Coverage not as described"}</span>
        )}
        <span>{formatDate(review.created_at)}</span>
      </p>
    </article>
  );
}

/** Reviews on the product page: the summary, every published review, and the way to add one. */
export function ProductReviews({
  productId,
  productSlug,
  summary,
  reviews,
}: {
  productId: string;
  productSlug: string;
  summary: ReviewSummary;
  reviews: readonly Review[];
}) {
  return (
    <section id="reviews" aria-labelledby="reviews-heading" className="mx-auto max-w-6xl scroll-mt-24 px-5 py-16">
      <p className="text-xs tracking-[0.25em] text-muted-foreground uppercase">From those who wore it</p>
      <h2 id="reviews-heading" className="mt-3 font-display text-display-sm leading-tight">
        Reviews
      </h2>
      <div className="mt-8">
        {summary.count > 0 ? (
          <Summary summary={summary} />
        ) : (
          <p className="text-muted-foreground">No reviews yet. If you have worn this piece, yours would be the first.</p>
        )}
      </div>
      <div className="mt-8">
        <ReviewForm productId={productId} productSlug={productSlug} />
      </div>
      {reviews.length > 0 && (
        <div className="mt-8">
          {reviews.map((review) => (
            <ReviewCard key={review.id} review={review} />
          ))}
        </div>
      )}
    </section>
  );
}
