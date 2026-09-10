import Link from "next/link";

import { Button } from "@/components/ui/button";
import {
  Card,
  CardBody,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { EmptyState } from "@/components/ui/empty-state";
import { features } from "@/lib/feature-registry";
import { siteConfig } from "@/lib/site";

export default function HomePage() {
  return (
    <div className="d-flex flex-column gap-4">
      <section className="mb-2">
        <h1 className="h2 fw-bold text-dark mb-2">{siteConfig.name}</h1>
        <p className="text-secondary lead fs-6 mb-0" style={{ maxWidth: "42rem" }}>
          {siteConfig.description}
        </p>
      </section>

      <section>
        <h2 className="h5 fw-semibold text-dark mb-3">Funciones disponibles</h2>
        {features.length === 0 ? (
          <EmptyState
            title="Aún no hay funciones implementadas"
            description="Las características del negocio aparecerán aquí a medida que se implementen."
          />
        ) : (
          <div className="row g-3 row-cols-1 row-cols-md-2 row-cols-lg-3">
            {features.map((feature) => {
              const Icon = feature.icon;
              return (
                <div key={feature.slug} className="col">
                  <Card className="h-100 d-flex flex-column">
                    <CardHeader>
                      <div className="d-flex align-items-center gap-3">
                        <div
                          className="d-flex align-items-center justify-content-center rounded bg-primary-subtle text-primary shrink-0"
                          style={{ width: "2.5rem", height: "2.5rem" }}
                        >
                          {Icon ? <Icon size={20} /> : <span className="fw-bold fs-6">{feature.title.charAt(0)}</span>}
                        </div>
                        <div>
                          <CardTitle>{feature.title}</CardTitle>
                        </div>
                      </div>
                      <CardDescription className="mt-2">{feature.description}</CardDescription>
                    </CardHeader>
                    <CardBody className="mt-auto pt-3">
                      <Link href={feature.route} className="text-decoration-none">
                        <Button variant="outline" size="sm" className="w-100">
                          Abrir
                        </Button>
                      </Link>
                    </CardBody>
                  </Card>
                </div>
              );
            })}
          </div>
        )}
      </section>
    </div>
  );
}

