import { Categories } from "./categories";

export interface Product {
  id: string;
  category: string;
  title: string;
  description: string;
  image: string;
  price: number;
}
