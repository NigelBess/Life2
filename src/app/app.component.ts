import { CommonModule } from '@angular/common';
import { Component, ElementRef, OnDestroy, ViewChild } from '@angular/core';
import { FormsModule } from '@angular/forms';
import { Subscription } from 'rxjs';
import { Life2ApiService, Life2Event } from './life2-api.service';

type StatusKind = 'waiting' | 'starting' | 'connected' | 'evolving' | 'error';
type MessageRole = 'agent' | 'user' | 'status';

interface Message {
  role: MessageRole;
  content: string;
  meta?: string;
}

@Component({
  selector: 'app-root',
  standalone: true,
  imports: [CommonModule, FormsModule],
  templateUrl: './app.component.html',
  styleUrl: './app.component.css',
})
export class AppComponent implements OnDestroy {
  @ViewChild('messagesPane') private messagesPane?: ElementRef<HTMLDivElement>;

  messages: Message[] = [];
  draft = '';
  apiKey = '';
  apiError = '';
  showKeyOverlay = true;
  keySubmitting = false;
  sendPending = false;
  statusKind: StatusKind = 'waiting';
  statusText = 'waiting for agent';
  generation?: number;

  private eventsSub?: Subscription;

  constructor(private readonly api: Life2ApiService) {
    this.connectEvents();
    this.api.checkKey().subscribe({
      next: (result) => {
        if (result.has_key) {
          this.showKeyOverlay = false;
          this.startAgent();
        }
      },
      error: () => this.setStatus('error', 'backend unavailable'),
    });
  }

  ngOnDestroy(): void {
    this.eventsSub?.unsubscribe();
  }

  submitKey(): void {
    const key = this.apiKey.trim();
    if (!key) {
      this.apiError = 'Please enter a key.';
      return;
    }

    this.keySubmitting = true;
    this.apiError = '';
    this.api.setKey(key).subscribe({
      next: (result) => {
        if (!result.ok) {
          this.apiError = result.error ?? 'Could not save key.';
          this.keySubmitting = false;
          return;
        }
        this.showKeyOverlay = false;
        this.apiKey = '';
        this.startAgent();
      },
      error: () => {
        this.apiError = 'Could not reach the backend.';
        this.keySubmitting = false;
      },
    });
  }

  send(): void {
    const text = this.draft.trim();
    if (!text || this.sendPending) {
      return;
    }

    this.addMessage({ role: 'user', content: text });
    this.draft = '';
    this.sendPending = true;

    this.api.send(text).subscribe({
      next: (result) => {
        this.sendPending = false;
        if (result.queued) {
          this.addMessage({ role: 'status', content: 'message queued until agent connects' });
        }
      },
      error: () => {
        this.sendPending = false;
        this.addMessage({ role: 'status', content: 'send failed; backend is not reachable' });
        this.setStatus('error', 'backend unavailable');
      },
    });
  }

  onDraftKeydown(event: KeyboardEvent): void {
    if (event.key === 'Enter' && !event.shiftKey) {
      event.preventDefault();
      this.send();
    }
  }

  private connectEvents(): void {
    this.eventsSub = this.api.events().subscribe({
      next: (event) => this.handleEvent(event),
      error: () => this.setStatus('error', 'event stream disconnected'),
    });
  }

  private startAgent(): void {
    this.setStatus('starting', 'starting agent');
    this.addMessage({ role: 'status', content: 'starting agent' });
    this.api.startAgent().subscribe({
      next: (result) => {
        if (!result.ok) {
          this.setStatus('error', 'agent failed to start');
          this.addMessage({ role: 'status', content: result.error ?? 'agent failed to start' });
        }
      },
      error: () => {
        this.setStatus('error', 'agent failed to start');
        this.addMessage({ role: 'status', content: 'agent failed to start' });
      },
    });
  }

  private handleEvent(event: Life2Event): void {
    if (event.type === 'message') {
      this.addMessage({
        role: 'agent',
        content: event.content,
        meta: `Life2 gen ${event.generation}`,
      });
      return;
    }

    if (event.status === 'connected') {
      this.generation = event.generation;
      this.setStatus('connected', `gen ${event.generation} active`);
      this.addMessage({ role: 'status', content: `connected generation ${event.generation}` });
    } else if (event.status === 'starting') {
      this.setStatus('starting', 'starting agent');
    } else if (event.status === 'evolving') {
      this.setStatus('evolving', 'evolving');
      this.addMessage({ role: 'status', content: 'evolving' });
    } else {
      this.setStatus('waiting', event.status);
    }
  }

  private setStatus(kind: StatusKind, text: string): void {
    this.statusKind = kind;
    this.statusText = text;
  }

  private addMessage(message: Message): void {
    this.messages = [...this.messages, message];
    queueMicrotask(() => {
      const pane = this.messagesPane?.nativeElement;
      if (pane) {
        pane.scrollTop = pane.scrollHeight;
      }
    });
  }
}
