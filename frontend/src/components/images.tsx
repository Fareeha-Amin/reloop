import { useQuery } from '@tanstack/react-query';
import { useEffect, useMemo, useState } from 'react';

import { ApiError } from '../api/errors';
import { client } from '../app/api';
import { t } from '../i18n';
import { Spinner } from '../ui/feedback';
import { Icon } from '../ui/icons';

/**
 * Donation images are served only to authorised viewers, so a plain <img src> (which
 * cannot send the bearer token) will not do: fetch the bytes, show an object URL.
 */
function useImageUrl(donationId: string, imageId: string) {
  const query = useQuery({
    queryKey: ['image', donationId, imageId],
    staleTime: Infinity,
    queryFn: async () => {
      const { data, response } = await client.GET('/donations/{donation_id}/images/{image_id}', {
        params: { path: { donation_id: donationId, image_id: imageId } },
        parseAs: 'blob',
      });
      if (!response.ok || !data) throw new ApiError(response.status, null, {}, []);
      return data as Blob;
    },
  });
  const url = useMemo(() => (query.data ? URL.createObjectURL(query.data) : null), [query.data]);
  useEffect(() => () => {
    if (url) URL.revokeObjectURL(url);
  }, [url]);
  return { url, isError: query.isError };
}

function AuthImage({ donationId, imageId, alt }: { donationId: string; imageId: string; alt: string }) {
  const { url, isError } = useImageUrl(donationId, imageId);
  return (
    <div className="grid aspect-square place-items-center overflow-hidden rounded-control bg-surface-muted text-ink-muted">
      {url ? (
        <img src={url} alt={alt} className="size-full object-cover" />
      ) : isError ? (
        <Icon name="alert" />
      ) : (
        <Spinner />
      )}
    </div>
  );
}

export function ImageGallery({ donationId, imageIds }: { donationId: string; imageIds: string[] }) {
  if (imageIds.length === 0) return <p className="text-sm text-ink-muted">{t('images.none')}</p>;
  return (
    <div className="grid grid-cols-3 gap-2 sm:grid-cols-4">
      {imageIds.map((id, index) => (
        <AuthImage key={id} donationId={donationId} imageId={id} alt={t('images.alt', { n: index + 1 })} />
      ))}
    </div>
  );
}

/**
 * Choose photos before upload, with local previews. The server validates them, enforces
 * the per-donation limit (no copy of it here) and strips metadata such as GPS.
 */
export function PhotoPicker({ files, onChange }: { files: File[]; onChange: (files: File[]) => void }) {
  const [previews, setPreviews] = useState<string[]>([]);
  useEffect(() => {
    const urls = files.map((f) => URL.createObjectURL(f));
    setPreviews(urls);
    return () => urls.forEach((u) => URL.revokeObjectURL(u));
  }, [files]);

  return (
    <div>
      <div className="grid grid-cols-3 gap-3 sm:grid-cols-6">
        {previews.map((url, index) => (
          <div key={url} className="group relative aspect-square overflow-hidden rounded-control bg-surface-muted">
            <img src={url} alt={t('images.alt', { n: index + 1 })} className="size-full object-cover" />
            <button
              type="button"
              onClick={() => onChange(files.filter((_, i) => i !== index))}
              className="absolute top-1 right-1 grid size-7 place-items-center rounded-full bg-ink/70 text-surface opacity-90 hover:opacity-100"
              aria-label={t('images.remove')}
            >
              <Icon name="x" className="size-4" />
            </button>
          </div>
        ))}
        <label className="grid aspect-square cursor-pointer place-items-center rounded-control border-2 border-dashed border-line-strong bg-surface text-ink-muted transition hover:border-brand-400 hover:text-brand-600">
          <span className="flex flex-col items-center gap-1 text-xs font-semibold">
            <Icon name="camera" className="size-6" />
            {t('images.add')}
          </span>
          <input
            type="file"
            accept="image/jpeg,image/png,image/webp"
            multiple
            className="sr-only"
            onChange={(e) => {
              const chosen = Array.from(e.target.files ?? []);
              onChange([...files, ...chosen]);
              e.target.value = '';
            }}
          />
        </label>
      </div>
      <p className="mt-2 text-xs text-ink-muted">{t('images.hint')}</p>
    </div>
  );
}
