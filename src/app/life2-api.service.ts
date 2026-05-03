import { Injectable, NgZone } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { Observable } from 'rxjs';

export interface KeyStatus {
  has_key: boolean;
}

export interface ApiResult {
  ok: boolean;
  error?: string;
}

export interface SendResult extends ApiResult {
  queued: boolean;
}

export type Life2Event =
  | { type: 'message'; content: string; generation: number }
  | { type: 'activity'; content: string; generation?: number }
  | { type: 'status'; status: 'starting' | 'connected' | 'evolving' | string; generation?: number };

@Injectable({ providedIn: 'root' })
export class Life2ApiService {
  constructor(
    private readonly http: HttpClient,
    private readonly zone: NgZone,
  ) {}

  checkKey(): Observable<KeyStatus> {
    return this.http.get<KeyStatus>('/api/check-key');
  }

  setKey(key: string): Observable<ApiResult> {
    return this.http.post<ApiResult>('/api/set-key', { key });
  }

  startAgent(): Observable<ApiResult & { already_running?: boolean }> {
    return this.http.post<ApiResult & { already_running?: boolean }>('/api/start-agent', {});
  }

  send(content: string): Observable<SendResult> {
    return this.http.post<SendResult>('/api/send', { content });
  }

  events(): Observable<Life2Event> {
    return new Observable<Life2Event>((subscriber) => {
      const source = new EventSource('/api/events');

      source.onmessage = (event) => {
        this.zone.run(() => {
          subscriber.next(JSON.parse(event.data) as Life2Event);
        });
      };

      source.onerror = () => {
        // EventSource automatically retries transient disconnects.
      };

      return () => source.close();
    });
  }
}
