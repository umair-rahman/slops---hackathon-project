"use client";

import { useMemo } from "react";
import {
  Bar,
  BarChart,
  CartesianGrid,
  Cell,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";

import { getScoreColor } from "@/lib/types";

interface Props {
  /** 10 buckets: 0-9, 10-19, ..., 90-100 */
  distribution: number[];
}

export function ScoreHistogram({ distribution }: Props) {
  const data = useMemo(
    () =>
      distribution.map((count, i) => ({
        bucket: `${i * 10}-${i * 10 + 9}`,
        count,
        center: i * 10 + 5,
      })),
    [distribution]
  );

  const total = distribution.reduce((a, b) => a + b, 0);
  if (total === 0) {
    return (
      <div className="card-gradient-border rounded-xl p-7">
        <h3 className="font-serif text-xl mb-2">score distribution</h3>
        <p className="text-[#737373] text-sm">No data to display.</p>
      </div>
    );
  }

  return (
    <div className="card-gradient-border rounded-xl p-7">
      <div className="flex items-center justify-between mb-4">
        <h3 className="font-serif text-xl">score distribution</h3>
        <span className="chip">{total} reviews</span>
      </div>
      <div className="h-64 -ml-4">
        <ResponsiveContainer width="100%" height="100%">
          <BarChart data={data} margin={{ top: 8, right: 8, left: -8, bottom: 0 }}>
            <CartesianGrid strokeDasharray="3 3" stroke="rgba(250,250,249,0.05)" />
            <XAxis
              dataKey="bucket"
              tick={{ fill: "#737373", fontSize: 10, fontFamily: "JetBrains Mono" }}
              axisLine={{ stroke: "rgba(250,250,249,0.1)" }}
              tickLine={false}
            />
            <YAxis
              tick={{ fill: "#737373", fontSize: 10, fontFamily: "JetBrains Mono" }}
              axisLine={{ stroke: "rgba(250,250,249,0.1)" }}
              tickLine={false}
            />
            <Tooltip
              cursor={{ fill: "rgba(250,204,21,0.05)" }}
              contentStyle={{
                background: "#0a0a0a",
                border: "1px solid rgba(250,250,249,0.1)",
                borderRadius: "8px",
                fontSize: "12px",
              }}
              labelStyle={{ color: "#facc15" }}
            />
            <Bar dataKey="count" radius={[4, 4, 0, 0]}>
              {data.map((entry, i) => (
                <Cell key={i} fill={getScoreColor(entry.center)} />
              ))}
            </Bar>
          </BarChart>
        </ResponsiveContainer>
      </div>
      <div className="flex justify-between mt-2 text-[10px] text-[#737373] font-mono px-2">
        <span>likely human</span>
        <span>uncertain</span>
        <span>likely AI</span>
      </div>
    </div>
  );
}
