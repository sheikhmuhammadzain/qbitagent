import { BarChart, Bar, LineChart, Line, AreaChart, Area, PieChart, Pie, Cell, XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer } from 'recharts';

interface ChartSpec {
  chart: 'bar' | 'line' | 'area' | 'pie';
  x: string;
  y: string;
  data: any[];
}

interface ChartRendererProps {
  spec: ChartSpec;
}

const COLORS = ['#0088FE', '#00C49F', '#FFBB28', '#FF8042', '#8884D8', '#82CA9D', '#FFC658', '#FF6B9D'];

export const ChartRenderer = ({ spec }: ChartRendererProps) => {
  const { chart, x, y, data } = spec;

  if (!data || data.length === 0) {
    return (
      <div className="p-4 text-center text-muted-foreground text-sm">
        No data available for chart
      </div>
    );
  }

  // Common chart configuration
  const chartConfig = {
    margin: { top: 10, right: 30, left: 0, bottom: 0 },
  };

  return (
    <div className="w-full bg-card/30 rounded-lg p-4 border border-border/50 my-3">
      <div className="mb-2 text-sm font-semibold text-foreground">
        📊 {chart.charAt(0).toUpperCase() + chart.slice(1)} Chart
      </div>
      <ResponsiveContainer width="100%" height={300}>
        {chart === 'bar' && (
          <BarChart data={data} {...chartConfig}>
            <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.1)" />
            <XAxis 
              dataKey={x} 
              tick={{ fill: 'rgba(255,255,255,0.7)', fontSize: 12 }}
              stroke="rgba(255,255,255,0.3)"
            />
            <YAxis 
              tick={{ fill: 'rgba(255,255,255,0.7)', fontSize: 12 }}
              stroke="rgba(255,255,255,0.3)"
            />
            <Tooltip 
              contentStyle={{ 
                backgroundColor: 'rgba(0,0,0,0.9)', 
                border: '1px solid rgba(255,255,255,0.2)',
                borderRadius: '8px',
                fontSize: '12px'
              }}
            />
            <Legend wrapperStyle={{ fontSize: '12px' }} />
            <Bar dataKey={y} fill="#0088FE" radius={[8, 8, 0, 0]} />
          </BarChart>
        )}

        {chart === 'line' && (
          <LineChart data={data} {...chartConfig}>
            <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.1)" />
            <XAxis 
              dataKey={x} 
              tick={{ fill: 'rgba(255,255,255,0.7)', fontSize: 12 }}
              stroke="rgba(255,255,255,0.3)"
            />
            <YAxis 
              tick={{ fill: 'rgba(255,255,255,0.7)', fontSize: 12 }}
              stroke="rgba(255,255,255,0.3)"
            />
            <Tooltip 
              contentStyle={{ 
                backgroundColor: 'rgba(0,0,0,0.9)', 
                border: '1px solid rgba(255,255,255,0.2)',
                borderRadius: '8px',
                fontSize: '12px'
              }}
            />
            <Legend wrapperStyle={{ fontSize: '12px' }} />
            <Line 
              type="monotone" 
              dataKey={y} 
              stroke="#00C49F" 
              strokeWidth={2}
              dot={{ r: 4 }}
              activeDot={{ r: 6 }}
            />
          </LineChart>
        )}

        {chart === 'area' && (
          <AreaChart data={data} {...chartConfig}>
            <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.1)" />
            <XAxis 
              dataKey={x} 
              tick={{ fill: 'rgba(255,255,255,0.7)', fontSize: 12 }}
              stroke="rgba(255,255,255,0.3)"
            />
            <YAxis 
              tick={{ fill: 'rgba(255,255,255,0.7)', fontSize: 12 }}
              stroke="rgba(255,255,255,0.3)"
            />
            <Tooltip 
              contentStyle={{ 
                backgroundColor: 'rgba(0,0,0,0.9)', 
                border: '1px solid rgba(255,255,255,0.2)',
                borderRadius: '8px',
                fontSize: '12px'
              }}
            />
            <Legend wrapperStyle={{ fontSize: '12px' }} />
            <Area 
              type="monotone" 
              dataKey={y} 
              stroke="#FFBB28" 
              fill="#FFBB28" 
              fillOpacity={0.6}
            />
          </AreaChart>
        )}

        {chart === 'pie' && (
          <PieChart>
            <Pie
              data={data}
              dataKey={y}
              nameKey={x}
              cx="50%"
              cy="50%"
              outerRadius={100}
              label={(entry) => `${entry[x]}: ${entry[y]}`}
              labelStyle={{ fontSize: '11px', fill: 'rgba(255,255,255,0.9)' }}
            >
              {data.map((entry, index) => (
                <Cell key={`cell-${index}`} fill={COLORS[index % COLORS.length]} />
              ))}
            </Pie>
            <Tooltip 
              contentStyle={{ 
                backgroundColor: 'rgba(0,0,0,0.9)', 
                border: '1px solid rgba(255,255,255,0.2)',
                borderRadius: '8px',
                fontSize: '12px'
              }}
            />
          </PieChart>
        )}
      </ResponsiveContainer>
      <div className="mt-2 text-xs text-muted-foreground">
        {data.length} data points • {x} vs {y}
      </div>
    </div>
  );
};
