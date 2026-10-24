import { Tag } from '../ui/Tag';
import { offerResponseTone, statusTone, urgencyTone, verificationTone, vocabLabel } from '../vocab/display';

export function StatusTag({ status, size = 'sm' }: { status: string; size?: 'sm' | 'md' }) {
  return (
    <Tag tone={statusTone(status)} dot size={size}>
      {vocabLabel('DonationStatus', status)}
    </Tag>
  );
}

export function OfferResponseTag({ response }: { response: string }) {
  return <Tag tone={offerResponseTone(response)}>{vocabLabel('OfferResponse', response)}</Tag>;
}

export function UrgencyTag({ urgency }: { urgency: string }) {
  return <Tag tone={urgencyTone(urgency)}>{vocabLabel('Urgency', urgency)}</Tag>;
}

export function VerificationTag({ status }: { status: string }) {
  return (
    <Tag tone={verificationTone(status)} dot>
      {vocabLabel('VerificationStatus', status)}
    </Tag>
  );
}
