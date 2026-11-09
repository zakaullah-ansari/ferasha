import { MapPin, Phone } from "lucide-react";
import type { Metadata } from "next";

import { HelpPage } from "@/components/site/PolicyView";
import { ATELIER } from "@/lib/brand";
import { CONTACT_TO_CONFIRM } from "@/lib/policies";

export const metadata: Metadata = {
  title: "Contact",
  description: `Visit or call ${ATELIER.name} in Kurla, Mumbai.`,
};

export default function ContactPage() {
  return (
    <HelpPage
      path="/contact"
      eyebrow="The atelier"
      title="Contact us"
      summary="For sizing, bespoke fittings, an order or anything else, the atelier is a call away."
      toConfirm={CONTACT_TO_CONFIRM}
    >
      <section className="grid gap-6 sm:grid-cols-2">
        <div>
          <h2 className="font-display text-2xl">Call</h2>
          <a
            href={ATELIER.phoneHref}
            className="mt-3 inline-flex items-center gap-2 text-lg underline-offset-4 hover:underline"
          >
            <Phone aria-hidden="true" className="size-4 text-muted-foreground" />
            {ATELIER.phoneDisplay}
          </a>
        </div>
        <div>
          <h2 className="font-display text-2xl">Visit</h2>
          <address className="mt-3 flex gap-2 leading-relaxed text-muted-foreground not-italic">
            <MapPin aria-hidden="true" className="mt-1 size-4 shrink-0" />
            <span>
              <span className="block text-foreground">{ATELIER.name}</span>
              {ATELIER.addressLines.map((line) => (
                <span key={line} className="block">
                  {line}
                </span>
              ))}
            </span>
          </address>
        </div>
      </section>

      <section>
        <h2 className="font-display text-2xl">Grievance officer</h2>
        <p className="mt-3 leading-relaxed text-muted-foreground">
          Under the Consumer Protection (E-Commerce) Rules, 2020, complaints can be raised with our grievance officer.
          We acknowledge every complaint within 48 hours and aim to resolve it within one month. Until the officer’s
          details are published here, call the atelier on {ATELIER.phoneDisplay}.
        </p>
      </section>
    </HelpPage>
  );
}
