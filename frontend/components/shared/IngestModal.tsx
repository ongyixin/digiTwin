"use client";

/**
 * IngestModal — legacy shim that renders ArtifactModal.
 * Kept for backward compatibility with existing imports.
 */
import { ArtifactModal } from "@/components/shared/ArtifactModal";

interface IngestModalProps {
  trigger?: React.ReactNode;
}

export function IngestModal({ trigger }: IngestModalProps) {
  return <ArtifactModal trigger={trigger} />;
}
