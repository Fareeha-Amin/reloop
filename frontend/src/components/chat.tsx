import { useMutation, useQueryClient } from '@tanstack/react-query';
import { useEffect, useRef, useState, type FormEvent, type KeyboardEvent } from 'react';
import { useSearchParams } from 'react-router';

import { unwrap } from '../api/errors';
import type { ChatMessageOut, ChatSummaryOut, ChatThreadOut } from '../api/schema';
import { client } from '../app/api';
import { CHAT_PARAM, CHAT_PARAM_OPEN } from '../app/paths';
import { chatKey, keys, useChats } from '../app/queries';
import { useSession } from '../app/session';
import { useReadState } from '../app/unread';
import { UNREAD_BADGE_MAX } from '../config';
import { formatDateTime, formatRelative } from '../i18n/format';
import { t } from '../i18n';
import { Button } from '../ui/Button';
import { Drawer } from '../ui/Drawer';
import { Alert, LoadingBlock } from '../ui/feedback';
import { TextArea } from '../ui/form';
import { Icon } from '../ui/icons';
import { Chips } from '../ui/Tabs';
import { Tag } from '../ui/Tag';
import { vocabLabel } from '../vocab/display';
import { ApiErrorAlert, fieldError } from './ApiErrorAlert';

/** Whose conversation this is, for wording only. Access is the API's decision. */
type Audience = 'donor' | 'organisation';

const badge = (count: number) => (count > UNREAD_BADGE_MAX ? `${UNREAD_BADGE_MAX}+` : String(count));

/** Queries whose `chat` summary changes when a thread is read. */
function useRefreshSummaries(donationId: string) {
  const queryClient = useQueryClient();
  return () => {
    queryClient.invalidateQueries({ queryKey: keys.donation(donationId) });
    queryClient.invalidateQueries({ queryKey: keys.myDonations });
    queryClient.invalidateQueries({ queryKey: ['held'] });
  };
}

function Bubble({ message }: { message: ChatMessageOut }) {
  const who = message.mine ? t('chat.you') : (message.sender_name ?? vocabLabel('Actor', message.sender));
  return (
    <li className={`flex flex-col ${message.mine ? 'items-end' : 'items-start'}`}>
      <div
        className={`max-w-[85%] rounded-card px-3.5 py-2 text-[15px] break-words whitespace-pre-wrap ${
          message.mine ? 'rounded-br-control bg-brand-700 text-brand-50' : 'rounded-bl-control bg-surface-muted text-ink'
        }`}
      >
        {message.body}
      </div>
      <p className="mt-1 px-1 text-xs text-ink-muted" title={formatDateTime(message.at)}>
        {who} · {formatRelative(message.at)}
      </p>
    </li>
  );
}

function Composer({ thread, onSent }: { thread: ChatThreadOut; onSent: () => void }) {
  const queryClient = useQueryClient();
  const [body, setBody] = useState('');
  const send = useMutation({
    mutationFn: (text: string) =>
      unwrap(client.POST('/chats/{thread_id}/messages', { params: { path: { thread_id: thread.id } }, body: { body: text } })),
    onSuccess: (updated) => {
      setBody('');
      queryClient.setQueryData<ChatThreadOut[]>(chatKey(thread.donation_id), (threads) =>
        threads?.map((existing) => (existing.id === updated.id ? updated : existing)),
      );
      onSent();
    },
    // A 409 means the thread just closed: refetch so the panel shows why.
    onError: () => queryClient.invalidateQueries({ queryKey: chatKey(thread.donation_id) }),
  });

  function submit(event?: FormEvent) {
    event?.preventDefault();
    if (body.trim() && !send.isPending) send.mutate(body);
  }

  function onKeyDown(event: KeyboardEvent<HTMLTextAreaElement>) {
    if (event.key === 'Enter' && !event.shiftKey && !event.nativeEvent.isComposing) {
      event.preventDefault();
      submit();
    }
  }

  return (
    <form onSubmit={submit} className="space-y-2">
      <ApiErrorAlert error={send.error} inlineFields={{ body: true }} />
      <div className="flex items-end gap-2">
        <TextArea
          className="min-w-0 flex-1"
          label={t('chat.messageLabel')}
          hideLabel
          placeholder={t('chat.placeholder')}
          rows={2}
          value={body}
          onChange={(e) => setBody(e.target.value)}
          onKeyDown={onKeyDown}
          error={fieldError(send.error, 'body')}
        />
        <Button type="submit" icon="arrowRight" busy={send.isPending} disabled={!body.trim()} aria-label={t('chat.send')}>
          <span className="hidden sm:inline">{t('chat.send')}</span>
        </Button>
      </div>
      <p className="text-xs text-ink-muted">{t('chat.messageHint')}</p>
    </form>
  );
}

/** Mark what the panel shows as read: on the server (the unread counts) and in the feed. */
function useMarkShown(thread: ChatThreadOut | undefined, open: boolean) {
  const queryClient = useQueryClient();
  const refreshSummaries = useRefreshSummaries(thread?.donation_id ?? '');
  const { user } = useSession();
  const { markRead: markNotificationsRead } = useReadState(user?.id ?? null);
  const lastSent = useRef<number | null>(null);

  const read = useMutation({
    mutationFn: ({ threadId, upTo }: { threadId: string; upTo: number }) =>
      unwrap(client.POST('/chats/{thread_id}/read', { params: { path: { thread_id: threadId } }, body: { up_to_message_id: upTo } })),
    onSuccess: (updated) => {
      queryClient.setQueryData<ChatThreadOut[]>(chatKey(updated.donation_id), (threads) =>
        threads?.map((existing) => (existing.id === updated.id ? updated : existing)),
      );
      refreshSummaries();
    },
  });

  const newest = thread?.messages.at(-1);
  const shownKeys = (thread?.messages ?? []).flatMap((m) => (m.notification_key ? [{ key: m.notification_key, at: m.at }] : []));
  const signature = shownKeys.map((k) => k.key).join();

  useEffect(() => {
    if (!open || !thread || !newest) return;
    if (shownKeys.length > 0) markNotificationsRead(...shownKeys);
    if (thread.unread > 0 && lastSent.current !== newest.id) {
      lastSent.current = newest.id;
      read.mutate({ threadId: thread.id, upTo: newest.id });
    }
    // When the panel opens, the thread changes, or new messages arrive.
  }, [open, thread?.id, newest?.id, thread?.unread, signature]); // eslint-disable-line react-hooks/exhaustive-deps
}

function ThreadBody({ thread }: { thread: ChatThreadOut }) {
  const end = useRef<HTMLDivElement>(null);
  const count = thread.messages.length;
  useEffect(() => {
    end.current?.scrollIntoView({ block: 'end' });
  }, [count, thread.id]);

  return (
    <div className="space-y-4">
      {count > 0 ? (
        <ul className="space-y-3" aria-live="polite">
          {thread.messages.map((m) => (
            <Bubble key={m.id} message={m} />
          ))}
        </ul>
      ) : (
        <div className="grid place-items-center px-4 py-12 text-center">
          <span className="grid size-12 place-items-center rounded-full bg-brand-50 text-brand-600">
            <Icon name="message" className="size-6" />
          </span>
          <p className="mt-3 max-w-xs text-sm text-ink-muted">{t('chat.empty')}</p>
        </div>
      )}
      {!thread.can_write && (
        <Alert kind="info" title={t('chat.closedTitle')}>
          {thread.closed_reason ? vocabLabel('ChatClosure', thread.closed_reason) : t('chat.closedGeneric')}
        </Alert>
      )}
      <div ref={end} />
    </div>
  );
}

function ChatPanel({
  donationId,
  audience,
  about,
  open,
  onClose,
}: {
  donationId: string;
  audience: Audience;
  about: string;
  open: boolean;
  onClose: () => void;
}) {
  const chats = useChats(donationId, open);
  const refreshSummaries = useRefreshSummaries(donationId);
  const threads = chats.data ?? [];
  const [selectedId, setSelectedId] = useState<string | null>(null);
  // The newest thread unless the user picked an earlier one.
  const thread = threads.find((th) => th.id === selectedId) ?? threads[0];
  useMarkShown(thread, open);

  // The other party: the organisation for the donor, "The donor" for the organisation.
  const title = thread ? (audience === 'donor' ? thread.organization_name : t('chat.theDonor')) : t('chat.title');

  return (
    <Drawer
      open={open}
      onClose={onClose}
      eyebrow={t('chat.eyebrow')}
      title={title}
      subtitle={t('chat.about', { item: about })}
      closeLabel={t('common.close')}
      toolbar={
        threads.length > 1 && (
          <div className="space-y-2">
            <p className="text-xs text-ink-muted">{t('chat.threadsNote')}</p>
            <Chips
              label={t('chat.threads')}
              value={thread?.id ?? null}
              onChange={(id) => setSelectedId(id)}
              items={threads.map((th, index) => ({
                value: th.id,
                label: index === 0 ? t('chat.threadCurrent', { org: th.organization_name }) : t('chat.threadEarlier', { org: th.organization_name }),
                icon: th.can_write ? 'message' : 'lock',
                count: th.unread > 0 ? th.unread : undefined,
              }))}
            />
          </div>
        )
      }
      footer={thread?.can_write ? <Composer key={thread.id} thread={thread} onSent={refreshSummaries} /> : undefined}
    >
      <ApiErrorAlert error={chats.error} />
      {chats.isPending ? <LoadingBlock label={t('common.loading')} /> : thread && <ThreadBody thread={thread} />}
    </Drawer>
  );
}

/**
 * The chat button on a donation page, shown only when the API reports a thread for this
 * viewer (`summary`). The count is the API's unread count. The panel's open state is in
 * the URL (?chat=open), so a notification can link straight to it.
 */
export function ChatButton({
  donationId,
  summary,
  audience,
  about,
  size = 'md',
}: {
  donationId: string;
  summary: ChatSummaryOut;
  audience: Audience;
  about: string;
  size?: 'md' | 'lg';
}) {
  const [params, setParams] = useSearchParams();
  const open = params.get(CHAT_PARAM) === CHAT_PARAM_OPEN;
  const setOpen = (value: boolean) =>
    setParams(
      (current) => {
        const next = new URLSearchParams(current);
        if (value) next.set(CHAT_PARAM, CHAT_PARAM_OPEN);
        else next.delete(CHAT_PARAM);
        return next;
      },
      { replace: true },
    );
  const label = summary.unread > 0 ? t('chat.buttonUnread', { count: summary.unread }) : t('chat.button');

  return (
    <>
      <Button variant="secondary" size={size} icon="message" onClick={() => setOpen(true)} aria-label={label} className="relative">
        {t('chat.buttonShort')}
        {summary.unread > 0 && (
          <span className="grid h-5 min-w-5 place-items-center rounded-pill bg-clay-500 px-1.5 text-[11px] font-bold text-surface" aria-hidden="true">
            {badge(summary.unread)}
          </span>
        )}
      </Button>
      <ChatPanel donationId={donationId} audience={audience} about={about} open={open} onClose={() => setOpen(false)} />
    </>
  );
}

/** On a donation in a dashboard list: new messages, without opening anything. */
export function UnreadMessagesTag({ summary }: { summary: ChatSummaryOut | null | undefined }) {
  if (!summary || summary.unread === 0) return null;
  return (
    <Tag tone="info" icon="message">
      {t('chat.newMessages', { count: summary.unread })}
    </Tag>
  );
}
