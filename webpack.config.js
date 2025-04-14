const path = require("path")

module.exports = {
  mode: "production",
  entry: "./static/js/main.js",
  output: {
    filename: "main.bundle.js",
    path: path.resolve(__dirname, "static/dist"),
  },
  module: {
    rules: [
      {
        test: /\.js$/,
        exclude: /node_modules/,
        use: {
          loader: "babel-loader",
          options: {
            presets: ["@babel/preset-env"],
          },
        },
      },
    ],
  },
}
