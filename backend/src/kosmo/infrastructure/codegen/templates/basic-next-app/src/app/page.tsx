import Link from "next/link";

import { Button } from "@/components/ui/button";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { EmptyState } from "@/components/ui/empty-state";
import { features } from "@/lib/feature-registry";
import { siteConfig } from "@/lib/site";

export default function HomePage() {
  return (
    <div className="flex flex-col gap-8">
      <section className="flex flex-col gap-2">
        <h1 className="text-2xl font-bold tracking-tight text-neutral-900">{siteConfig.name}</h1>
        <p className="max-w-2xl text-sm leading-6 text-neutral-600">{siteConfig.description}</p>
      </section>

      <section className="flex flex-col gap-4">
        <h2 className="text-lg font-semibold text-neutral-900">Funciones disponibles</h2>
        {features.length === 0 ? (
          <EmptyState
            title="Aún no hay funciones implementadas"
            description="Las características del negocio aparecerán aquí a medida que se implementen."
          />
        ) : (
          <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
            {features.map((feature) => (
              <Card key={feature.slug}>
                <CardHeader>
                  <div className="flex items-center gap-3">
                    <div className="flex h-10 w-10 shrink-0 items-center justify-center rounded-md bg-indigo-50">
                      <feature.icon className="h-5 w-5 text-indigo-600" />
                    </div>
                    <CardTitle>{feature.title}</CardTitle>
                  </div>
                  <CardDescription>{feature.description}</CardDescription>
                </CardHeader>
                <CardContent>
                  <Link href={feature.route}>
                    <Button variant="secondary" size="sm" className="w-full">
                      Abrir
                    </Button>
                  </Link>
                </CardContent>
              </Card>
            ))}
          </div>
        )}
      </section>
    </div>
  );
}
