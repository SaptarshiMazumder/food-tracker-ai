declare module 'react-native-event-source' {
  export default class RNEventSource {
    constructor(url: string, options?: any);
    addEventListener(event: string, listener: (e: { data: string }) => void): void;
    close(): void;
    onopen?: () => void;
    onmessage?: (e: { data: string }) => void;
    onerror?: (e: any) => void;
  }
}


