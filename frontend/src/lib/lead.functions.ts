import { createServerFn } from "@tanstack/react-start";

import { leadSchema } from "./lead-schema";
import { deliverLead } from "./lead.server";

/**
 * Server function = javni HTTP endpoint. Validacija Zodom NIJE opcionalna.
 * CSRF zaštitu dodaje createCsrfMiddleware u src/start.ts.
 */
export const submitLead = createServerFn({ method: "POST" })
  .validator((data: unknown) => leadSchema.parse(data))
  .handler(async ({ data }) => {
    await deliverLead(data);
    return { ok: true as const };
  });
