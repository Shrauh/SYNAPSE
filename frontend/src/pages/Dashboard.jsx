import React from "react";
import {
  AlertTriangle,
  CheckCircle,
  Activity,
  Server,
  BrainCircuit,
  ShieldAlert,
} from "lucide-react";

function Dashboard() {
  const recentIncidents = [
    {
      id: "INC-001",
      service: "Payment Service",
      severity: "Critical",
      status: "Open",
    },
    {
      id: "INC-002",
      service: "Auth Service",
      severity: "High",
      status: "Investigating",
    },
    {
      id: "INC-003",
      service: "Inventory Service",
      severity: "Medium",
      status: "Resolved",
    },
    {
      id: "INC-004",
      service: "Gateway",
      severity: "Low",
      status: "Closed",
    },
  ];

  return (
    <div className="p-8 bg-gray-100 min-h-screen">

      {/* Header */}

      <div className="mb-8">

        <h1 className="text-4xl font-bold text-gray-800">
          Dashboard
        </h1>

        <p className="text-gray-600 mt-2">
          Welcome to SYNAPSE AI Incident Response Platform
        </p>

      </div>

      {/* KPI Cards */}

      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">

        <div className="bg-white rounded-xl shadow p-6">
          <div className="flex justify-between items-center">
            <div>
              <p className="text-gray-500">Total Incidents</p>
              <h2 className="text-3xl font-bold mt-2">48</h2>
            </div>
            <AlertTriangle className="text-red-500" size={38} />
          </div>
        </div>

        <div className="bg-white rounded-xl shadow p-6">
          <div className="flex justify-between items-center">
            <div>
              <p className="text-gray-500">Open Incidents</p>
              <h2 className="text-3xl font-bold mt-2">12</h2>
            </div>
            <ShieldAlert className="text-orange-500" size={38} />
          </div>
        </div>

        <div className="bg-white rounded-xl shadow p-6">
          <div className="flex justify-between items-center">
            <div>
              <p className="text-gray-500">Resolved</p>
              <h2 className="text-3xl font-bold mt-2">30</h2>
            </div>
            <CheckCircle className="text-green-500" size={38} />
          </div>
        </div>

        <div className="bg-white rounded-xl shadow p-6">
          <div className="flex justify-between items-center">
            <div>
              <p className="text-gray-500">Healthy Services</p>
              <h2 className="text-3xl font-bold mt-2">18</h2>
            </div>
            <Server className="text-blue-500" size={38} />
          </div>
        </div>

      </div>

      {/* Middle Section */}

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6 mt-8">

        {/* Recent Incidents */}

        <div className="bg-white rounded-xl shadow p-6">

          <h2 className="text-2xl font-bold mb-4">
            Recent Incidents
          </h2>

          <table className="w-full">

            <thead>

              <tr className="text-left border-b">

                <th className="py-3">ID</th>

                <th>Service</th>

                <th>Severity</th>

                <th>Status</th>

              </tr>

            </thead>

            <tbody>

              {recentIncidents.map((item) => (

                <tr key={item.id} className="border-b hover:bg-gray-50">

                  <td className="py-4">{item.id}</td>

                  <td>{item.service}</td>

                  <td>

                    <span className={`px-3 py-1 rounded-full text-white
                      ${
                        item.severity === "Critical"
                          ? "bg-red-600"
                          : item.severity === "High"
                          ? "bg-orange-500"
                          : item.severity === "Medium"
                          ? "bg-yellow-500"
                          : "bg-green-500"
                      }`}>

                      {item.severity}

                    </span>

                  </td>

                  <td>{item.status}</td>

                </tr>

              ))}

            </tbody>

          </table>

        </div>

        {/* AI Summary */}

        <div className="bg-white rounded-xl shadow p-6">

          <div className="flex items-center gap-3 mb-4">

            <BrainCircuit
              className="text-blue-600"
              size={35}
            />

            <h2 className="text-2xl font-bold">

              AI Incident Summary

            </h2>

          </div>

          <div className="space-y-5">

            <div className="bg-blue-50 p-4 rounded-lg">

              <p className="font-semibold">

                Root Cause Prediction

              </p>

              <p className="text-gray-600 mt-2">

                AI predicts a high probability that
                Payment Service outage is caused by
                increased database latency.

              </p>

            </div>

            <div className="bg-green-50 p-4 rounded-lg">

              <p className="font-semibold">

                Recommendation

              </p>

              <p className="text-gray-600 mt-2">

                Restart payment worker nodes,
                verify database health,
                and monitor queue latency.

              </p>

            </div>

            <div className="bg-yellow-50 p-4 rounded-lg">

              <p className="font-semibold">

                Risk Level

              </p>

              <p className="text-red-600 font-bold mt-2">

                HIGH

              </p>

            </div>

          </div>

        </div>

      </div>

      {/* Bottom Section */}

      <div className="grid md:grid-cols-3 gap-6 mt-8">

        <div className="bg-white shadow rounded-xl p-6">

          <Activity className="text-blue-500 mb-3" size={35} />

          <h2 className="font-bold text-xl">

            Service Health

          </h2>

          <p className="text-gray-600 mt-2">

            18 of 20 services are operating normally.

          </p>

        </div>

        <div className="bg-white shadow rounded-xl p-6">

          <AlertTriangle
            className="text-red-500 mb-3"
            size={35}
          />

          <h2 className="font-bold text-xl">

            Critical Alerts

          </h2>

          <p className="text-gray-600 mt-2">

            Two critical production alerts require immediate attention.

          </p>

        </div>

        <div className="bg-white shadow rounded-xl p-6">

          <BrainCircuit
            className="text-purple-600 mb-3"
            size={35}
          />

          <h2 className="font-bold text-xl">

            AI Confidence

          </h2>

          <p className="text-gray-600 mt-2">

            Root cause prediction confidence: <strong>96%</strong>

          </p>

        </div>

      </div>

    </div>
  );
}

export default Dashboard;
