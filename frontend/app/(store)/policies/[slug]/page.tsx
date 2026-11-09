import type { Metadata } from "next";
import { notFound } from "next/navigation";

import { HelpPage, PolicySections } from "@/components/site/PolicyView";
import { POLICIES, policy } from "@/lib/policies";

type Props = { params: Promise<{ slug: string }> };

export function generateStaticParams() {
  return POLICIES.map(({ slug }) => ({ slug }));
}

export const dynamicParams = false;

export async function generateMetadata({ params }: Props): Promise<Metadata> {
  const found = policy((await params).slug);
  return found ? { title: found.title, description: found.summary } : {};
}

export default async function PolicyPage({ params }: Props) {
  const found = policy((await params).slug);
  if (!found) notFound();
  return (
    <HelpPage
      path={`/policies/${found.slug}`}
      eyebrow={`Updated ${found.updated}`}
      title={found.title}
      summary={found.summary}
      toConfirm={found.toConfirm}
    >
      <PolicySections sections={found.sections} />
    </HelpPage>
  );
}
