import Foundation
import Vision
import ImageIO

func fail(_ code: String) -> Never {
    let payload = ["error": code]
    let data = try! JSONSerialization.data(withJSONObject: payload)
    FileHandle.standardOutput.write(data)
    exit(2)
}

guard CommandLine.arguments.count == 2 else { fail("missing_image_path") }
let url = URL(fileURLWithPath: CommandLine.arguments[1]) as CFURL
guard let source = CGImageSourceCreateWithURL(url, nil),
      let image = CGImageSourceCreateImageAtIndex(source, 0, nil) else {
    fail("image_decode_failed")
}

let request = VNRecognizeTextRequest()
request.recognitionLevel = .accurate
request.usesLanguageCorrection = false
request.recognitionLanguages = ["en-US"]

do {
    try VNImageRequestHandler(cgImage: image, options: [:]).perform([request])
} catch {
    fail("vision_request_failed")
}

let observations = request.results ?? []
let blocks: [[String: Any]] = observations.compactMap { observation in
    let top = observation.topCandidates(3)
    guard let candidate = top.first else { return nil }
    let box = observation.boundingBox
    return [
        "text": candidate.string,
        "confidence": Double(candidate.confidence),
        "candidates": top.map { ["text": $0.string, "confidence": Double($0.confidence)] },
        "bounding_box": [
            "x": Double(box.origin.x), "y": Double(box.origin.y),
            "width": Double(box.size.width), "height": Double(box.size.height)
        ]
    ]
}

let os = ProcessInfo.processInfo.operatingSystemVersion
let payload: [String: Any] = [
    "engine": "macos_vision",
    "engine_version": "\(os.majorVersion).\(os.minorVersion).\(os.patchVersion)",
    "image_size": ["width": image.width, "height": image.height],
    "text_blocks": blocks,
    "processing_warnings": []
]

do {
    let data = try JSONSerialization.data(withJSONObject: payload)
    FileHandle.standardOutput.write(data)
} catch {
    fail("json_encoding_failed")
}
