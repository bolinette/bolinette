export default interface ApiResponse<T> {
  code: number;
  data: T;
  messages: string[];
  status: string;
}
