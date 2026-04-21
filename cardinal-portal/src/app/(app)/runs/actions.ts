"use server";

import { revalidatePath } from "next/cache";
import { deleteRun, deleteRunsBulk, type BulkDeleteResult } from "@/lib/api";

export async function deleteRunAction(id: string | number): Promise<{ deleted: number }> {
  const result = await deleteRun(id);
  revalidatePath("/runs");
  return result;
}

export async function deleteRunsAction(ids: Array<string | number>): Promise<BulkDeleteResult> {
  const result = await deleteRunsBulk(ids);
  revalidatePath("/runs");
  return result;
}
