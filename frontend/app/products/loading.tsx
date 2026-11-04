import { Skeleton } from "@/components/ui/skeleton";

/**
 * Arriving from another page. Changing a filter does not show this: the
 * transition keeps the current garments on screen, dimmed, until the new
 * ones are ready.
 */
export default function Loading() {
  return (
    <div aria-busy="true" aria-label="Loading the collection" className="mx-auto max-w-7xl px-5 pt-6 pb-24">
      <Skeleton className="h-4 w-40" />
      <Skeleton className="mt-12 h-3 w-36" />
      <Skeleton className="mt-4 h-10 w-72" />
      <div className="mt-10 lg:grid lg:grid-cols-[15rem_1fr] lg:gap-12">
        <div className="hidden space-y-4 lg:block">
          {Array.from({ length: 6 }, (_, index) => (
            <Skeleton key={index} className="h-6 w-full" />
          ))}
        </div>
        <div>
          <Skeleton className="h-9 w-full" />
          <div className="mt-8 grid grid-cols-2 gap-x-5 gap-y-12 xl:grid-cols-3">
            {Array.from({ length: 6 }, (_, index) => (
              <div key={index}>
                <Skeleton className="aspect-[4/5] w-full rounded-lg" />
                <Skeleton className="mt-3 h-5 w-3/4" />
                <Skeleton className="mt-2 h-4 w-1/3" />
              </div>
            ))}
          </div>
        </div>
      </div>
    </div>
  );
}
