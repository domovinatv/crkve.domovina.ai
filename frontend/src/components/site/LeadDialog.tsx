import { useState } from "react";
import { useServerFn } from "@tanstack/react-start";
import { CheckCircle2 } from "lucide-react";

import { Button } from "@/components/ui/button";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from "@/components/ui/dialog";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Textarea } from "@/components/ui/textarea";
import { leadFields } from "@/data/lead-form";
import { site } from "@/data/site";
import { leadSchema } from "@/lib/lead-schema";
import { submitLead } from "@/lib/lead.functions";

type Errors = Record<string, string>;

type Props = {
  label?: string;
  title?: string;
  description?: string;
  /** Predpopunjena polja, npr. { service: "Naziv usluge" } sa stranice usluge. */
  defaults?: Record<string, string>;
  variant?: "default" | "outline" | "secondary";
  size?: "default" | "lg" | "sm";
  className?: string;
};

export function LeadDialog({
  label = "POŠALJITE UPIT",
  title = "Pošaljite upit",
  description = "Javit ćemo vam se s informacijama u najkraćem roku.",
  defaults = {},
  variant = "default",
  size = "lg",
  className,
}: Props) {
  const [open, setOpen] = useState(false);
  const [done, setDone] = useState(false);
  const [pending, setPending] = useState(false);
  const [errors, setErrors] = useState<Errors>({});
  const send = useServerFn(submitLead);

  async function onSubmit(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (pending) return;

    const form = new FormData(event.currentTarget);
    const payload = Object.fromEntries(
      leadFields.map((f) => [f.name, String(form.get(f.name) ?? "")]),
    );

    const parsed = leadSchema.safeParse(payload);
    if (!parsed.success) {
      const next: Errors = {};
      for (const issue of parsed.error.issues) {
        const key = String(issue.path[0] ?? "form");
        if (!next[key]) next[key] = issue.message;
      }
      setErrors(next);
      return;
    }

    setErrors({});
    setPending(true);
    try {
      await send({ data: parsed.data });
      setDone(true);
    } catch {
      setErrors({
        form: `Slanje nije uspjelo. Pokušajte ponovno ili nas nazovite na ${site.phone}.`,
      });
    } finally {
      setPending(false);
    }
  }

  function onOpenChange(next: boolean) {
    setOpen(next);
    if (!next) {
      setDone(false);
      setErrors({});
    }
  }

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogTrigger asChild>
        <Button variant={variant} size={size} className={className}>
          {label}
        </Button>
      </DialogTrigger>
      <DialogContent className="max-h-[92svh] overflow-y-auto sm:max-w-lg">
        {done ? (
          <div className="py-6 text-center">
            <CheckCircle2 className="mx-auto size-10 text-primary" aria-hidden="true" />
            <DialogTitle className="mt-4 text-lg">Upit je zaprimljen</DialogTitle>
            <DialogDescription className="mt-2">
              Hvala vam. Javit ćemo se s informacijama u najkraćem roku.
            </DialogDescription>
            <Button className="mt-6" onClick={() => onOpenChange(false)}>
              Zatvori
            </Button>
          </div>
        ) : (
          <>
            <DialogHeader>
              <DialogTitle>{title}</DialogTitle>
              <DialogDescription>{description}</DialogDescription>
            </DialogHeader>

            <form onSubmit={onSubmit} noValidate className="mt-2 space-y-4">
              {leadFields.map((field) => {
                const error = errors[field.name];
                const common = {
                  id: field.name,
                  name: field.name,
                  defaultValue: defaults[field.name] ?? "",
                  "aria-invalid": Boolean(error),
                  "aria-describedby": error ? `${field.name}-error` : undefined,
                  ...(field.placeholder ? { placeholder: field.placeholder } : {}),
                  ...(field.maxLength ? { maxLength: field.maxLength } : {}),
                };

                return (
                  <div key={field.name} className="space-y-1.5">
                    <Label htmlFor={field.name}>
                      {field.label}
                      {field.required && <span aria-hidden="true"> *</span>}
                    </Label>

                    {field.type === "textarea" ? (
                      <Textarea {...common} rows={4} />
                    ) : field.type === "select" ? (
                      <select
                        {...common}
                        className="flex h-9 w-full rounded-md border border-input bg-transparent px-3 py-1 text-sm shadow-xs"
                      >
                        <option value="">Odaberite…</option>
                        {field.options?.map((option) => (
                          <option key={option} value={option}>
                            {option}
                          </option>
                        ))}
                      </select>
                    ) : (
                      <Input {...common} type={field.type} />
                    )}

                    {field.hint && !error && (
                      <p className="text-xs text-muted-foreground">{field.hint}</p>
                    )}
                    {error && (
                      <p
                        id={`${field.name}-error`}
                        className="text-xs font-semibold text-destructive"
                      >
                        {error}
                      </p>
                    )}
                  </div>
                );
              })}

              {errors["form"] && (
                <p className="text-sm font-semibold text-destructive">{errors["form"]}</p>
              )}

              <Button type="submit" className="w-full" disabled={pending}>
                {pending ? "Šaljem…" : "Pošalji upit"}
              </Button>
              <p className="text-xs text-muted-foreground">
                Slanjem obrasca pristajete na obradu podataka radi odgovora na upit.
              </p>
            </form>
          </>
        )}
      </DialogContent>
    </Dialog>
  );
}
