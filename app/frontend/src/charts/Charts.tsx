import {
  Bar,
  BarChart,
  CartesianGrid,
  Cell,
  Line,
  LineChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import type { ChartPoint } from "../types";

const ACCENT = "#2563eb";
const MUTED = "#cbd5e1";

function ChartCard({
  title,
  children,
  wide = false,
}: {
  title: string;
  children: React.ReactNode;
  wide?: boolean;
}) {
  return (
    <section className={wide ? "card wide" : "card"}>
      <h2>{title}</h2>
      <div style={{ height: 250 }}>{children}</div>
    </section>
  );
}

function EmptyChart({ title, wide = false, message }: { title: string; wide?: boolean; message: string }) {
  return (
    <section className={wide ? "card wide" : "card"}>
      <h2>{title}</h2>
      <div className="card-empty">{message}</div>
    </section>
  );
}

export function BarSeries({
  title,
  data,
  layout = "vertical",
  onSelect,
  selected,
  wide = false,
}: {
  title: string;
  data: ChartPoint[];
  layout?: "vertical" | "horizontal";
  onSelect?: (label: string) => void;
  selected?: string[];
  wide?: boolean;
}) {
  if (!data.length) {
    return (
      <EmptyChart
        title={title}
        wide={wide}
        message="Aucune donnée pour ce graphique avec le périmètre actuel."
      />
    );
  }
  const horizontal = layout === "horizontal";
  return (
    <ChartCard title={title} wide={wide}>
      <ResponsiveContainer>
        <BarChart data={data} layout={horizontal ? "vertical" : "horizontal"} margin={{ left: 4, right: 8, top: 4, bottom: 0 }}>
          <CartesianGrid strokeDasharray="3 3" stroke="#eef0f4" vertical={!horizontal} />
          {horizontal ? (
            <>
              <XAxis type="number" tick={{ fontSize: 11, fill: "#6b7280" }} axisLine={false} tickLine={false} />
              <YAxis type="category" dataKey="label" width={84} tick={{ fontSize: 11, fill: "#6b7280" }} axisLine={false} tickLine={false} />
            </>
          ) : (
            <>
              <XAxis dataKey="label" tick={{ fontSize: 11, fill: "#6b7280" }} axisLine={false} tickLine={false} />
              <YAxis tick={{ fontSize: 11, fill: "#6b7280" }} axisLine={false} tickLine={false} />
            </>
          )}
          <Tooltip
            cursor={{ fill: "rgba(37, 99, 235, 0.06)" }}
            contentStyle={{
              borderRadius: 10,
              border: "1px solid #e8eaef",
              boxShadow: "0 8px 24px rgba(15,20,25,0.08)",
              fontSize: 12,
            }}
            formatter={(value: number, _name, item) => [
              `${Number(value).toFixed(2)}${item?.payload?.count ? ` · ${item.payload.count} obs.` : ""}`,
              title,
            ]}
          />
          <Bar
            dataKey="value"
            radius={[5, 5, 0, 0]}
            onClick={(point) => onSelect?.(String(point.label))}
            cursor={onSelect ? "pointer" : "default"}
          >
            {data.map((entry) => (
              <Cell
                key={entry.label}
                fill={selected?.length && !selected.includes(entry.label) ? MUTED : ACCENT}
              />
            ))}
          </Bar>
        </BarChart>
      </ResponsiveContainer>
    </ChartCard>
  );
}

export function LineSeries({ title, data }: { title: string; data: ChartPoint[] }) {
  if (!data.length) {
    return <EmptyChart title={title} wide message="Aucune série temporelle pour ce périmètre." />;
  }
  return (
    <ChartCard title={title} wide>
      <ResponsiveContainer>
        <LineChart data={data} margin={{ left: 4, right: 8, top: 8, bottom: 0 }}>
          <CartesianGrid strokeDasharray="3 3" stroke="#eef0f4" />
          <XAxis dataKey="label" tick={{ fontSize: 11, fill: "#6b7280" }} axisLine={false} tickLine={false} />
          <YAxis tick={{ fontSize: 11, fill: "#6b7280" }} domain={["auto", "auto"]} axisLine={false} tickLine={false} />
          <Tooltip
            contentStyle={{
              borderRadius: 10,
              border: "1px solid #e8eaef",
              boxShadow: "0 8px 24px rgba(15,20,25,0.08)",
              fontSize: 12,
            }}
          />
          <Line type="monotone" dataKey="value" stroke={ACCENT} strokeWidth={2.2} dot={{ r: 3, strokeWidth: 0 }} activeDot={{ r: 5 }} />
        </LineChart>
      </ResponsiveContainer>
    </ChartCard>
  );
}
