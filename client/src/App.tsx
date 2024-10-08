import { useState } from "react";
// import "./App.css";
import axios from "axios";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Button } from "@/components/ui/button";
import {
  ChartConfig,
  ChartContainer,
  ChartTooltip,
  ChartTooltipContent,
  ChartLegend,
  ChartLegendContent,
} from "@/components/ui/chart";
import { CartesianGrid, Line, LineChart, XAxis, YAxis } from "recharts";

interface GlucoseData {
  hour: number;
  historic_glucose: number;
}

const chartConfig = {
  hour: {
    label: "Hour",
    color: "#2563eb",
  },
  historic_glucose: {
    label: "Historic Glucose",
    color: "#60a5fa",
  },
} satisfies ChartConfig;

function App() {
  const [glucoseData, setGlucoseData] = useState<GlucoseData[] | null>(null);

  const handleFileUpload = async (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files) {
      const file = e.target.files[0];

      const formData = new FormData();
      formData.append("file", file);

      try {
        await axios.post("http://localhost:8000/upload-csv/", formData);
        alert("CSV uploaded successfully");
      } catch (error) {
        console.error("Error uploading CSV:", error);
      }
    }
  };

  const fetchGlucoseTrends = async () => {
    try {
      const response = await axios.get<GlucoseData[]>(
        "http://localhost:8000/glucose-trends/",
        {
          params: {
            insulin_type: "long_acting_insulin",
            min_dose: 6,
            max_dose: 8,
          },
        }
      );
      setGlucoseData(response.data);
    } catch (error) {
      console.error("Error fetching glucose trends:", error);
    }
  };

  return (
    <div className="container mx-auto p-4">
      <h1 className="text-3xl font-bold mb-4">Glucose Data Analyzer</h1>
      <Card className="mb-4">
        <CardHeader>
          <CardTitle>Upload CSV</CardTitle>
        </CardHeader>
        <CardContent>
          <Input type="file" onChange={handleFileUpload} className="mb-2" />
          <Button onClick={fetchGlucoseTrends}>Analyze Glucose Trends</Button>
        </CardContent>
      </Card>
      {glucoseData && (
        <Card>
          <CardHeader>
            <CardTitle>Glucose Trends</CardTitle>
          </CardHeader>
          <CardContent>
            <ChartContainer
              config={chartConfig}
              className="min-h-[200px] w-full"
            >
              <LineChart data={glucoseData}>
                <CartesianGrid strokeDasharray="3 3" />
                <XAxis dataKey="hour" />
                <YAxis />
                <ChartTooltip content={<ChartTooltipContent />} />
                <ChartLegend content={<ChartLegendContent />} />
                <Line
                  dataKey="historic_glucose"
                  stroke="var(--color-historic-glucose)"
                />
              </LineChart>
            </ChartContainer>
          </CardContent>
        </Card>
      )}
    </div>
  );
}

export default App;
